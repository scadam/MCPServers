import type { WorkerProfile } from "../types";

const Field = ({ label, value }: { label: string; value?: string }) => (
  <div className="field">
    <p className="label">{label}</p>
    <p className="value">{value ?? "—"}</p>
  </div>
);

export const WorkerProfileCard = ({ worker }: { worker: WorkerProfile }) => (
  <article className="worker-card">
    <div className="identity">
      <div className="avatar" aria-hidden>
        {worker.name
          .split(" ")
          .map((part) => part[0])
          .join("")
          .slice(0, 2)}
      </div>
      <div>
        <h2>{worker.name}</h2>
        <p>{worker.businessTitle}</p>
        <a href={`mailto:${worker.email}`} className="link">
          {worker.email}
        </a>
      </div>
    </div>

    <div className="grid">
      <Field label="Workday ID" value={worker.workdayId} />
      <Field label="Worker ID" value={worker.workerId} />
      <Field
        label="Location"
        value={
          worker.location && worker.locationId ? `${worker.location} (${worker.locationId})` : worker.location || worker.locationId
        }
      />
      <Field
        label="Country"
        value={
          worker.country && worker.countryCode ? `${worker.country} (${worker.countryCode})` : worker.country || worker.countryCode
        }
      />
      <Field label="Organization" value={worker.supervisoryOrganization} />
      <Field
        label="Job profile"
        value={
          worker.jobProfile && worker.jobType ? `${worker.jobProfile} • ${worker.jobType}` : worker.jobProfile || worker.jobType
        }
      />
      <Field
        label="Primary job"
        value={
          worker.primaryJobDescriptor && worker.primaryJobId
            ? `${worker.primaryJobDescriptor} (${worker.primaryJobId})`
            : worker.primaryJobDescriptor || worker.primaryJobId
        }
      />
    </div>
  </article>
);
