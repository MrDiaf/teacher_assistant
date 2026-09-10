import { Icon } from "../ui";

function PlaceholderPage({ title, copy }: { title: string; copy: string }) {
  return (
    <main className="placeholder-page" aria-labelledby="placeholder-title">
      <div className="placeholder-mark" aria-hidden="true">
        <Icon name="leaf" size={28} />
      </div>
      <p className="eyebrow">Teacher Assistant</p>
      <h1 id="placeholder-title">{title}</h1>
      <p>{copy}</p>
      <span>Coming in a later phase</span>
    </main>
  );
}

export function DashboardPage() {
  return (
    <PlaceholderPage
      title="Dashboard"
      copy="Your teaching overview will come together here in a later phase."
    />
  );
}

export function StudyPlanPage() {
  return (
    <PlaceholderPage
      title="Study Plan"
      copy="Study planning tools are coming in a later phase."
    />
  );
}
