import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import { Icon } from "../../platform/ui";
import { documentsApi } from "./api";
import { DeleteProjectDialog, ProjectDialog } from "./DocumentDialogs";
import type { DocumentProject, DocumentTag } from "./types";

function formatModified(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DocumentsPage() {
  const [projects, setProjects] = useState<DocumentProject[]>([]);
  const [tags, setTags] = useState<DocumentTag[]>([]);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<DocumentProject | null | undefined>(
    undefined,
  );
  const [deleting, setDeleting] = useState<DocumentProject | null>(null);
  const [opened, setOpened] = useState<DocumentProject | null>(null);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#f4c75f");
  const [busyProject, setBusyProject] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const [nextProjects, nextTags] = await Promise.all([
          documentsApi.list(search, tagFilter, signal),
          documentsApi.listTags(signal),
        ]);
        setProjects(nextProjects);
        setTags(nextTags);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Documents could not be loaded.",
          );
        }
      } finally {
        setLoading(false);
      }
    },
    [search, tagFilter],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load]);

  async function saveProject(title: string) {
    const saved = editing
      ? await documentsApi.rename(editing.id, title)
      : await documentsApi.create(title);
    setEditing(undefined);
    setOpened(editing ? (opened?.id === saved.id ? saved : opened) : saved);
    await load();
  }

  async function deleteProject() {
    if (!deleting) return;
    await documentsApi.delete(deleting.id);
    if (opened?.id === deleting.id) setOpened(null);
    setDeleting(null);
    await load();
  }

  async function createTag(event: FormEvent) {
    event.preventDefault();
    if (!newTagName.trim()) return;
    setError(null);
    try {
      await documentsApi.createTag(newTagName.trim(), newTagColor);
      setNewTagName("");
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The tag could not be created.",
      );
    }
  }

  async function deleteTag(tag: DocumentTag) {
    setError(null);
    try {
      await documentsApi.deleteTag(tag.id);
      if (tagFilter === tag.id) setTagFilter(null);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The tag could not be deleted.",
      );
    }
  }

  async function setTag(
    project: DocumentProject,
    tagId: string,
    assigned: boolean,
  ) {
    setBusyProject(project.id);
    setError(null);
    try {
      const updated = assigned
        ? await documentsApi.assignTag(project.id, tagId)
        : await documentsApi.unassignTag(project.id, tagId);
      setProjects((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      if (opened?.id === updated.id) setOpened(updated);
      const nextTags = await documentsApi.listTags();
      setTags(nextTags);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The project tag could not be changed.",
      );
    } finally {
      setBusyProject(null);
    }
  }

  const activeTag = useMemo(
    () => tags.find((tag) => tag.id === tagFilter),
    [tagFilter, tags],
  );

  return (
    <main className="documents-page" aria-labelledby="documents-title">
      <header className="documents-header">
        <div>
          <p className="eyebrow">Private LaTeX workspace</p>
          <h1 id="documents-title">Documents</h1>
          <p>
            Create, organize, and recover source projects stored only on this
            installation.
          </p>
        </div>
        <button
          className="primary-button create-document-button"
          onClick={() => setEditing(null)}
          type="button"
        >
          <Icon name="plus" size={18} /> New project
        </button>
      </header>

      {error && (
        <div className="documents-error" role="alert">
          <strong>Documents need attention</strong>
          <span>{error}</span>
          <button onClick={() => void load()} type="button">
            Retry
          </button>
        </div>
      )}

      <section className="documents-toolbar" aria-label="Project filters">
        <label>
          <span>Search projects</span>
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by title"
            type="search"
            value={search}
          />
        </label>
        <div className="document-tag-filters" aria-label="Filter by tag">
          <button
            aria-pressed={tagFilter === null}
            onClick={() => setTagFilter(null)}
            type="button"
          >
            All projects
          </button>
          {tags.map((tag) => (
            <button
              aria-pressed={tagFilter === tag.id}
              key={tag.id}
              onClick={() => setTagFilter(tag.id)}
              style={{ "--tag-color": tag.color } as React.CSSProperties}
              type="button"
            >
              <span aria-hidden="true" /> {tag.name}
            </button>
          ))}
        </div>
      </section>

      <div className="documents-layout">
        <section className="document-project-area" aria-live="polite">
          {loading ? (
            <div className="document-loading" role="status">
              Loading private projects…
            </div>
          ) : projects.length === 0 ? (
            <div className="documents-empty">
              <span>
                <Icon name="file" size={28} />
              </span>
              <h2>
                {search || tagFilter
                  ? "No projects match these filters"
                  : "Start your first document"}
              </h2>
              <p>
                {search || tagFilter
                  ? `Try another title or ${activeTag ? `remove the ${activeTag.name} tag filter` : "clear the filters"}.`
                  : "Each project starts with a private, valid main.tex and can be included in coordinated backups."}
              </p>
              {(search || tagFilter) && (
                <button
                  className="quiet-button"
                  onClick={() => {
                    setSearch("");
                    setTagFilter(null);
                  }}
                  type="button"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="document-grid">
              {projects.map((project) => (
                <article
                  className={
                    opened?.id === project.id
                      ? "document-card selected"
                      : "document-card"
                  }
                  key={project.id}
                >
                  <button
                    className="document-card-open"
                    onClick={() => setOpened(project)}
                    type="button"
                  >
                    <span className="document-file-mark">
                      <Icon name="file" size={24} />
                    </span>
                    <span>
                      <strong>{project.title}</strong>
                      <small>
                        Modified {formatModified(project.updated_at)}
                      </small>
                    </span>
                  </button>
                  <div className="document-card-tags">
                    {project.tags.length ? (
                      project.tags.map((tag) => (
                        <span
                          key={tag.id}
                          style={
                            { "--tag-color": tag.color } as React.CSSProperties
                          }
                        >
                          {tag.name}
                        </span>
                      ))
                    ) : (
                      <small>Untagged</small>
                    )}
                  </div>
                  <div className="document-card-actions">
                    <button onClick={() => setOpened(project)} type="button">
                      Open
                    </button>
                    <button onClick={() => setEditing(project)} type="button">
                      Rename
                    </button>
                    <a href={documentsApi.sourceZipUrl(project.id)}>
                      Source ZIP
                    </a>
                    <button
                      className="danger-link"
                      onClick={() => setDeleting(project)}
                      type="button"
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <aside
          className="document-sidebar"
          aria-label="Document project details and tags"
        >
          {opened ? (
            <section className="document-detail">
              <p className="eyebrow">Selected project</p>
              <h2>{opened.title}</h2>
              <p>Created {formatModified(opened.created_at)}</p>
              <div className="document-downloads">
                <a href={documentsApi.mainTexUrl(opened.id)}>
                  <Icon name="file" size={16} /> Download main.tex
                </a>
                <a href={documentsApi.sourceZipUrl(opened.id)}>
                  <Icon name="download" size={16} /> Download source ZIP
                </a>
              </div>
              <h3>Project tags</h3>
              <div className="document-assignment-list">
                {tags.length === 0 ? (
                  <p>Create a tag below to classify this project.</p>
                ) : (
                  tags.map((tag) => {
                    const assigned = opened.tags.some(
                      (item) => item.id === tag.id,
                    );
                    return (
                      <label key={tag.id}>
                        <input
                          checked={assigned}
                          disabled={busyProject === opened.id}
                          onChange={(event) =>
                            void setTag(opened, tag.id, event.target.checked)
                          }
                          type="checkbox"
                        />
                        <span
                          style={
                            { "--tag-color": tag.color } as React.CSSProperties
                          }
                        />{" "}
                        {tag.name}
                      </label>
                    );
                  })
                )}
              </div>
            </section>
          ) : (
            <section className="document-detail-empty">
              <Icon name="file" size={24} />
              <h2>Choose a project</h2>
              <p>Open a project to download its source or change its tags.</p>
            </section>
          )}

          <section className="document-tag-manager">
            <h2>Tags</h2>
            <form onSubmit={createTag}>
              <label>
                <span>Tag name</span>
                <input
                  maxLength={64}
                  onChange={(event) => setNewTagName(event.target.value)}
                  placeholder="e.g. Research"
                  value={newTagName}
                />
              </label>
              <label>
                <span>Color</span>
                <input
                  aria-label="New tag color"
                  onChange={(event) => setNewTagColor(event.target.value)}
                  type="color"
                  value={newTagColor}
                />
              </label>
              <button className="quiet-button" type="submit">
                Add tag
              </button>
            </form>
            {tags.length > 0 && (
              <ul>
                {tags.map((tag) => (
                  <li key={tag.id}>
                    <span
                      style={{ background: tag.color }}
                      aria-hidden="true"
                    />
                    <strong>{tag.name}</strong>
                    <small>
                      {tag.project_count}{" "}
                      {tag.project_count === 1 ? "project" : "projects"}
                    </small>
                    <button
                      aria-label={`Delete tag ${tag.name}`}
                      onClick={() => void deleteTag(tag)}
                      type="button"
                    >
                      <Icon name="x" size={15} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>

      {editing !== undefined && (
        <ProjectDialog
          project={editing}
          onClose={() => setEditing(undefined)}
          onSave={saveProject}
        />
      )}
      {deleting && (
        <DeleteProjectDialog
          project={deleting}
          onClose={() => setDeleting(null)}
          onDelete={deleteProject}
        />
      )}
    </main>
  );
}
