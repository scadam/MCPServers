"""Workday MCP tool implementations."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from mcp.server.fastmcp import Context

from ..auth import EntraTokenValidator
from ..http import create_async_client
from ..logging import get_logger
from .helpers import build_worker_context, get_workday_access_token

LOGGER = get_logger(__name__)


def _get_auth_token(ctx: Optional[Context] = None) -> str:
    """Read the Entra access token exclusively from the Authorization header."""

    if ctx is None:
        raise ValueError("HTTP context not available; provide Authorization header")

    try:
        request = ctx.request_context.request
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Authorization header unavailable for this request") from exc

    auth_header = request.headers.get("authorization") if request else None
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise ValueError("Authorization bearer token is required in the request headers")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Authorization bearer token is required in the request headers")

    LOGGER.debug("auth_token_resolved_from_header")
    return token


def _transform_worker(worker_data: Dict[str, Any]) -> Dict[str, Any]:
    primary_job = worker_data.get("primaryJob", {})
    location = primary_job.get("location", {})
    country = location.get("country", {})
    return {
        "workdayId": worker_data.get("id"),
        "workerId": worker_data.get("workerId"),
        "name": worker_data.get("descriptor"),
        "email": worker_data.get("person", {}).get("email"),
        "workerType": worker_data.get("workerType", {}).get("descriptor"),
        "businessTitle": primary_job.get("businessTitle"),
        "location": location.get("descriptor"),
        "locationId": location.get("Location_ID"),
        "country": country.get("descriptor"),
        "countryCode": country.get("ISO_3166-1_Alpha-3_Code"),
        "supervisoryOrganization": primary_job.get("supervisoryOrganization", {}).get(
            "descriptor"
        ),
        "jobType": primary_job.get("jobType", {}).get("descriptor"),
        "jobProfile": primary_job.get("jobProfile", {}).get("descriptor"),
        "primaryJobId": primary_job.get("id"),
        "primaryJobDescriptor": primary_job.get("descriptor"),
    }


async def _fetch_json(url: str, access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    async with create_async_client() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def tool_get_worker(ctx: Optional[Context] = None) -> Dict[str, Any]:
    """Get the current Workday worker profile.
    
    Validates the Entra ID token and retrieves worker data using server's Workday credentials.
    """
    entra_token = _get_auth_token(ctx)
    # Validate Entra ID token and get worker context using server's Workday credentials
    worker_context = await build_worker_context(entra_token)
    return _transform_worker(worker_context.worker_data)


async def _get_leave_balances(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/"
        f"balances?worker={workday_id}"
    )
    data = await _fetch_json(url, access_token)
    balances = []
    for balance in data.get("data", []):
        plan = balance.get("absencePlan", {})
        balances.append(
            {
                "planName": plan.get("descriptor"),
                "planId": plan.get("id"),
                "balance": balance.get("quantity", "0"),
                "unit": balance.get("unit", {}).get("descriptor"),
                "effectiveDate": balance.get("effectiveDate"),
                "timeOffTypes": plan.get("timeoffs", ""),
            }
        )
    return balances


async def _get_eligible_absence_types(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/"
        f"workers/{workday_id}/eligibleAbsenceTypes"
    )
    data = await _fetch_json(url, access_token)
    absence_types = []
    for item in data.get("data", []):
        absence_types.append(
            {
                "name": item.get("descriptor"),
                "id": item.get("id"),
                "unit": item.get("unitOfTime", {}).get("descriptor"),
                "category": item.get("category", {}).get("descriptor"),
                "group": item.get("absenceTypeGroup", {}).get("descriptor"),
            }
        )
    return absence_types


async def _get_leaves_of_absence(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/"
        f"workers/{workday_id}/leavesOfAbsence"
    )
    data = await _fetch_json(url, access_token)
    leaves = []
    for item in data.get("data", []):
        leaves.append(
            {
                "id": item.get("id"),
                "leaveType": item.get("leaveType", {}).get("descriptor"),
                "status": item.get("status", {}).get("descriptor"),
                "firstDayOfLeave": item.get("firstDayOfLeave"),
                "lastDayOfWork": item.get("lastDayOfWork"),
                "estimatedLastDay": item.get("estimatedLastDayOfLeave"),
                "comment": item.get("latestLeaveComment", ""),
            }
        )
    return leaves


async def _get_time_off_details(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/"
        f"workers/{workday_id}/timeOffDetails"
    )
    data = await _fetch_json(url, access_token)
    details = []
    for item in data.get("data", []):
        details.append(
            {
                "date": item.get("date"),
                "timeOffType": item.get("timeOffType", {}).get("descriptor"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit", {}).get("descriptor"),
                "status": item.get("status", {}).get("descriptor"),
                "comment": item.get("comment", ""),
            }
        )
    return details


async def tool_get_leave_balances(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    workday_id = worker_context.workday_id
    access_token = worker_context.workday_access_token
    leave_balances, eligible_absence_types, leaves_of_absence, booked_time_off = await asyncio.gather(
        _get_leave_balances(access_token, workday_id),
        _get_eligible_absence_types(access_token, workday_id),
        _get_leaves_of_absence(access_token, workday_id),
        _get_time_off_details(access_token, workday_id),
    )
    return {
        "success": True,
        "leaveBalances": leave_balances,
        "eligibleAbsenceTypes": eligible_absence_types,
        "leavesOfAbsence": leaves_of_absence,
        "bookedTimeOff": booked_time_off,
    }


async def _fetch_direct_reports(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{workday_id}/directReports"
    )
    data = await _fetch_json(url, access_token)
    reports = []
    for item in data.get("data", []):
        reports.append(
            {
                "isManager": item.get("isManager"),
                "primaryWorkPhone": item.get("primaryWorkPhone"),
                "primaryWorkEmail": item.get("primaryWorkEmail"),
                "primarySupervisoryOrganization": item.get("primarySupervisoryOrganization", {}).get(
                    "descriptor"
                ),
                "businessTitle": item.get("businessTitle"),
                "descriptor": item.get("descriptor"),
            }
        )
    return reports


async def tool_get_direct_reports(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    reports = await _fetch_direct_reports(worker_context.workday_access_token, worker_context.workday_id)
    return {"success": True, "directReports": reports}


async def _fetch_inbox_tasks(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{workday_id}/inboxTasks"
    )
    data = await _fetch_json(url, access_token)
    tasks = []
    for item in data.get("data", []):
        tasks.append(
            {
                "assigned": item.get("assigned"),
                "due": item.get("due"),
                "initiator": item.get("initiator", {}).get("descriptor"),
                "status": item.get("status", {}).get("descriptor"),
                "stepType": item.get("stepType", {}).get("descriptor"),
                "subject": item.get("subject", {}).get("descriptor"),
                "overallProcess": item.get("overallProcess", {}).get("descriptor"),
                "descriptor": item.get("descriptor"),
            }
        )
    return tasks


async def tool_get_inbox_tasks(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    tasks = await _fetch_inbox_tasks(worker_context.workday_access_token, worker_context.workday_id)
    return {"success": True, "tasks": tasks}


async def _fetch_learning_assignments(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/service/customreport2/"
        "microsoft_dpt6/svasireddy/Required_Learning"
        f"?Worker_s__for_Learning_Assignment%21WID={workday_id}&format=json"
    )
    data = await _fetch_json(url, access_token)
    assignments = []
    for item in data.get("Report_Entry", []):
        assignments.append(
            {
                "assignmentStatus": item.get("assignmentStatus"),
                "dueDate": item.get("dueDate"),
                "learningContent": item.get("learningContent"),
                "overdue": item.get("overdue") == "1",
                "required": item.get("required") == "1",
                "workdayId": item.get("workdayId"),
            }
        )
    return assignments


async def tool_get_learning_assignments(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    assignments = await _fetch_learning_assignments(
        worker_context.workday_access_token, worker_context.workday_id
    )
    return {"success": True, "assignments": assignments, "total": len(assignments)}


async def _fetch_pay_slips(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{workday_id}/paySlips"
    )
    data = await _fetch_json(url, access_token)
    pay_slips = []
    for item in data.get("data", []):
        pay_slips.append(
            {
                "gross": item.get("gross"),
                "status": item.get("status", {}).get("descriptor"),
                "net": item.get("net"),
                "date": item.get("date"),
                "descriptor": item.get("descriptor"),
            }
        )
    return pay_slips


async def tool_get_pay_slips(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    pay_slips = await _fetch_pay_slips(worker_context.workday_access_token, worker_context.workday_id)
    return {"success": True, "paySlips": pay_slips}


async def _fetch_time_off_entries(access_token: str, workday_id: str) -> List[Dict[str, Any]]:
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{workday_id}/timeOffEntries"
    )
    data = await _fetch_json(url, access_token)
    entries = []
    for item in data.get("data", []):
        entries.append(
            {
                "employee": item.get("employee", {}).get("descriptor"),
                "timeOffRequestStatus": item.get("timeOffRequest", {}).get("status"),
                "timeOffRequestDescriptor": item.get("timeOffRequest", {}).get("descriptor"),
                "unitOfTime": item.get("unitOfTime", {}).get("descriptor"),
                "timeOffPlan": item.get("timeOff", {}).get("plan", {}).get("descriptor"),
                "timeOffDescriptor": item.get("timeOff", {}).get("descriptor"),
                "date": item.get("date"),
                "units": item.get("units"),
                "descriptor": item.get("descriptor"),
            }
        )
    return entries


async def tool_get_time_off_entries(ctx: Optional[Context] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    entries = await _fetch_time_off_entries(
        worker_context.workday_access_token, worker_context.workday_id
    )
    return {"success": True, "timeOffEntries": entries}


async def _get_default_dates() -> Dict[str, str]:
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    formatted = tomorrow.strftime("%Y-%m-%d")
    return {"startDate": formatted, "endDate": formatted}


async def tool_prepare_request_leave(ctx: Optional[Context] = None, startDate: Optional[str] = None, 
                                   endDate: Optional[str] = None, quantity: Optional[str] = None, 
                                   unit: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    default_dates = await _get_default_dates()
    request_params = {
        "startDate": startDate or default_dates["startDate"],
        "endDate": endDate or default_dates["endDate"],
        "quantity": quantity or "1",
        "unit": unit or "Days",
        "reason": reason or "Vacation",
    }
    access_token = worker_context.workday_access_token
    workday_id = worker_context.workday_id
    eligible_absence_types, leave_balances, booked_time_off = await asyncio.gather(
        _get_eligible_absence_types(access_token, workday_id),
        _get_leave_balances(access_token, workday_id),
        _get_time_off_details(access_token, workday_id),
    )
    return {
        "success": True,
        "requestParameters": request_params,
        "eligibleAbsenceTypes": eligible_absence_types,
        "leaveBalances": leave_balances,
        "bookedTimeOff": booked_time_off,
        "workdayId": workday_id,
        "bookingGuidance": {
            "timeFormat": "ISO 8601 with timezone (e.g., 2025-02-25T08:00:00.000Z)",
            "defaultWorkingHours": {"start": "08:00:00.000Z", "end": "17:00:00.000Z"},
            "quantityCalculation": {
                "forHours": "Use dailyDefaultQuantity * number of days",
                "forDays": "Use 1 per day requested",
            },
        },
    }


def _generate_date_range(start_date: str, end_date: str) -> Iterable[str]:
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    current = start
    while current <= end:
        yield current.date().isoformat()
        current += timedelta(days=1)


def _create_days_array(start_date: str, end_date: str, quantity: str, unit: str, reason: str, time_off_type_id: str) -> List[Dict[str, Any]]:
    days = []
    for day in _generate_date_range(start_date, end_date):
        daily_quantity = quantity
        if unit.lower() == "days":
            daily_quantity = "8"
        days.append(
            {
                "date": f"{day}T08:00:00.000Z",
                "start": f"{day}T08:00:00.000Z",
                "end": f"{day}T17:00:00.000Z",
                "dailyQuantity": daily_quantity,
                "comment": reason,
                "timeOffType": {"id": time_off_type_id},
            }
        )
    return days


async def tool_book_leave(ctx: Optional[Context] = None, startDate: str = None, endDate: str = None, 
                        timeOffTypeId: str = None, quantity: str = "8", unit: str = "Hours", 
                        reason: str = "Time off request") -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    worker_context = await build_worker_context(token)
    
    if not startDate or not endDate or not timeOffTypeId:
        raise ValueError("startDate, endDate, and timeOffTypeId are required")
    
    days = _create_days_array(startDate, endDate, quantity, unit, reason, timeOffTypeId)
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/absenceManagement/v1/microsoft_dpt6/"
        f"workers/{worker_context.workday_id}/requestTimeOff"
    )
    payload = {"days": days}
    headers = {
        "Authorization": f"Bearer {worker_context.workday_access_token}",
        "Content-Type": "application/json",
    }
    async with create_async_client() as client:
        response = await client.post(url, json=payload, headers=headers)
        content_type = response.headers.get("content-type", "")
        parsed_body: Any
        if "application/json" in content_type:
            parsed_body = response.json()
        else:
            parsed_body = {"message": response.text}
        if response.is_error:
            message = None
            if isinstance(parsed_body, dict):
                message = parsed_body.get("errors", [{}])[0].get("error") or parsed_body.get("error")
                if not message:
                    message = parsed_body.get("message")
            if not message:
                message = f"Workday API error {response.status_code}"
            raise ValueError(message)
    business_process = parsed_body.get("businessProcessParameters", {}).get(
        "overallBusinessProcess", {}
    ).get("descriptor")
    transaction_status = parsed_body.get("businessProcessParameters", {}).get(
        "transactionStatus", {}
    ).get("descriptor")
    days_booked = len(parsed_body.get("days", days))
    total_quantity = sum(float(day.get("dailyQuantity", 0)) for day in days)
    return {
        "success": True,
        "message": "Time off request submitted successfully",
        "bookingDetails": {
            "businessProcess": business_process,
            "status": parsed_body.get("businessProcessParameters", {}).get("overallStatus"),
            "transactionStatus": transaction_status,
            "daysBooked": days_booked,
            "totalQuantity": total_quantity,
        },
        "workdayResponse": parsed_body,
    }


async def tool_change_business_title(ctx: Optional[Context] = None, proposedBusinessTitle: str = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    if not proposedBusinessTitle:
        raise ValueError("proposedBusinessTitle is required")
    worker_context = await build_worker_context(token)
    url = (
        "https://wd2-impl-services1.workday.com/ccx/api/common/v1/microsoft_dpt6/"
        f"workers/{worker_context.workday_id}/businessTitleChanges?type=me"
    )
    headers = {
        "Authorization": f"Bearer {worker_context.workday_access_token}",
        "Content-Type": "application/json",
    }
    payload = {"proposedBusinessTitle": proposedBusinessTitle}
    async with create_async_client() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    return {"success": True, "message": "Business title change request submitted", "changeDetails": data}


async def _search_learning_content(access_token: str, skills: Iterable[str], topics: Iterable[str]) -> Dict[str, Any]:
    url = "https://wd2-impl-services1.workday.com/ccx/api/learning/v1/microsoft_dpt6/content"
    params: List[tuple[str, str]] = []
    for skill in skills:
        params.append(("skills", str(skill)))
    for topic in topics:
        params.append(("topics", str(topic)))
    async with create_async_client() as client:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        return response.json()


async def _get_lessons(access_token: str, content_id: str) -> Dict[str, Any]:
    url = f"https://wd2-impl-services1.workday.com/ccx/api/learning/v1/microsoft_dpt6/content/{content_id}/lessons"
    async with create_async_client() as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        return response.json()


def _flatten_lesson(lesson: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": lesson.get("id"),
        "descriptor": lesson.get("descriptor"),
        "description": lesson.get("description"),
        "order": lesson.get("order"),
        "required": lesson.get("required"),
        "contentType": lesson.get("contentType", {}).get("descriptor"),
        "duration": lesson.get("instructorLedData", {}).get("duration")
        or lesson.get("mediaData", {}).get("duration"),
        "contentURL": lesson.get("externalContentData", {}).get("contentURL"),
        "instructors": [i.get("descriptor") for i in lesson.get("instructorLedData", {}).get("instructors", [])],
        "materials": [m.get("descriptor") for m in lesson.get("trainingActivityData", {}).get("materials", [])],
        "activityType": lesson.get("trainingActivityData", {}).get("activityType", {}).get("descriptor"),
        "virtualClassroomURL": lesson.get("instructorLedData", {})
        .get("virtualClassroomData", {})
        .get("virtualClassroomURL"),
        "location": lesson.get("instructorLedData", {}).get("inPersonLedData", {}).get(
            "adhocLocationName"
        ),
        "trackAttendance": lesson.get("instructorLedData", {}).get("trackAttendance")
        or lesson.get("trainingActivityData", {}).get("trackAttendance"),
        "trackGrades": lesson.get("instructorLedData", {}).get("trackGrades")
        or lesson.get("trainingActivityData", {}).get("trackGrades"),
    }


def _flatten_content(content: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": content.get("id"),
        "descriptor": content.get("descriptor"),
        "description": content.get("description"),
        "contentNumber": content.get("contentNumber"),
        "contentURL": content.get("contentURL"),
        "version": content.get("version"),
        "createdOnDate": content.get("createdOnDate"),
        "averageRating": content.get("averageRating"),
        "ratingCount": content.get("ratingCount"),
        "popularity": content.get("popularity"),
        "contentType": content.get("contentType", {}).get("descriptor"),
        "contentProvider": content.get("contentProvider", {}).get("descriptor"),
        "accessType": content.get("accessType", {}).get("descriptor"),
        "deliveryMode": content.get("deliveryMode", {}).get("descriptor"),
        "skillLevel": content.get("skillLevel", {}).get("descriptor"),
        "lifecycleStatus": content.get("lifecycleStatus", {}).get("descriptor"),
        "availabilityStatus": content.get("availabilityStatus", {}).get("descriptor"),
        "excludeFromRecommendations": content.get("excludeFromRecommendations"),
        "excludeFromSearchAndBrowse": content.get("excludeFromSearchAndBrowse"),
        "learningCatalogs": [c.get("descriptor") for c in content.get("learningCatalogs", [])],
        "languages": [lang.get("descriptor") for lang in content.get("languages", [])],
        "skills": [s.get("descriptor") for s in content.get("skills", [])],
        "topics": [t.get("descriptor") for t in content.get("topics", [])],
        "securityCategories": [sc.get("descriptor") for sc in content.get("securityCategories", [])],
        "contactPersons": [cp.get("descriptor") for cp in content.get("contactPersons", [])],
        "imageURL": content.get("image", {}).get("publicURL"),
        "lessons": [],
    }


async def tool_search_learning_content(ctx: Optional[Context] = None, skills: Optional[List[str]] = None, 
                                      topics: Optional[List[str]] = None) -> Dict[str, Any]:
    token = _get_auth_token(ctx)
    validator = EntraTokenValidator()
    await validator.validate(token)
    access_token = await get_workday_access_token()

    def _normalize(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, Iterable):
            return [str(item) for item in value]
        return [str(value)]

    skills = _normalize(skills)
    topics = _normalize(topics)
    content_response = await _search_learning_content(access_token, skills, topics)
    items = content_response.get("data", [])
    enriched = []
    for item in items:
        flattened = _flatten_content(item)
        try:
            lessons_response = await _get_lessons(access_token, item.get("id"))
            flattened["lessons"] = [_flatten_lesson(lesson) for lesson in lessons_response.get("data", [])]
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("lesson_fetch_failed", content_id=item.get("id"), error=str(exc))
            flattened["lessons"] = []
        enriched.append(flattened)
    return {"success": True, "content": enriched, "total": len(enriched)}


WORKDAY_TOOL_SPECS: List[Dict[str, Any]] = [
    {"name": "get_worker", "func": tool_get_worker, "summary": "Get the current Workday worker profile."},
    {"name": "get_leave_balances", "func": tool_get_leave_balances, "summary": "Retrieve leave balances and related data."},
    {"name": "get_direct_reports", "func": tool_get_direct_reports, "summary": "List direct reports for the current worker."},
    {"name": "get_inbox_tasks", "func": tool_get_inbox_tasks, "summary": "List Workday inbox tasks for the current worker."},
    {"name": "get_learning_assignments", "func": tool_get_learning_assignments, "summary": "Retrieve required learning assignments."},
    {"name": "get_pay_slips", "func": tool_get_pay_slips, "summary": "List recent Workday pay slips."},
    {"name": "get_time_off_entries", "func": tool_get_time_off_entries, "summary": "List time off entries for the current worker."},
    {"name": "prepare_request_leave", "func": tool_prepare_request_leave, "summary": "Prepare the data needed to submit a leave request."},
    {"name": "book_leave", "func": tool_book_leave, "summary": "Submit a leave request to Workday for the current worker."},
    {"name": "change_business_title", "func": tool_change_business_title, "summary": "Request a business title change for the current worker."},
    {"name": "search_learning_content", "func": tool_search_learning_content, "summary": "Search Workday learning content and fetch associated lessons."},
]
