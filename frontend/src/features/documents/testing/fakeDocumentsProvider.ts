import type {
  DocumentProject,
  DocumentTag,
  DocumentTagSummary,
} from "../types";

const now = "2026-09-08T10:00:00Z";
const apiPrefix = "/api/v1";

export interface FakeDocumentsRequest {
  method: string;
  path: string;
  query: string;
}

interface FakeDocumentsSeed {
  projects?: DocumentProject[];
  tags?: DocumentTag[];
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function parseObjectBody(init?: RequestInit): Record<string, unknown> {
  if (typeof init?.body !== "string") {
    throw new Error("Documents fake expected a JSON string body.");
  }
  const body = JSON.parse(init.body) as unknown;
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Documents fake expected a JSON object body.");
  }
  return body as Record<string, unknown>;
}

function requireKeys(
  body: Record<string, unknown>,
  allowed: string[],
  required: string[] = [],
) {
  const unknown = Object.keys(body).filter((key) => !allowed.includes(key));
  if (unknown.length) {
    throw new Error(
      `Documents fake rejected unknown fields: ${unknown.join(", ")}.`,
    );
  }
  for (const key of required) {
    if (typeof body[key] !== "string" || !(body[key] as string).trim()) {
      throw new Error(`Documents fake requires a non-empty ${key}.`);
    }
  }
}

function copyProject(project: DocumentProject): DocumentProject {
  return { ...project, tags: project.tags.map((tag) => ({ ...tag })) };
}

export function createFakeDocumentsProvider(seed: FakeDocumentsSeed = {}) {
  let projects = (seed.projects ?? []).map(copyProject);
  let tags = (seed.tags ?? []).map((tag) => ({ ...tag }));
  let nextId = 1;
  const requests: FakeDocumentsRequest[] = [];

  function projectResponse(project: DocumentProject) {
    return copyProject(project);
  }

  function refreshCounts() {
    tags = tags.map((tag) => ({
      ...tag,
      project_count: projects.filter((project) =>
        project.tags.some((assigned) => assigned.id === tag.id),
      ).length,
    }));
  }

  async function fetch(
    input: string | URL | Request,
    init?: RequestInit,
  ): Promise<Response> {
    const url = new URL(String(input), "http://documents.test");
    const method =
      init?.method ?? (input instanceof Request ? input.method : "GET");
    if (!url.pathname.startsWith(apiPrefix)) {
      throw new Error(
        `Documents fake rejected a non-API request: ${url.pathname}.`,
      );
    }
    const path = url.pathname.slice(apiPrefix.length);
    requests.push({ method, path, query: url.search });

    if (method === "GET" && path === "/document-projects") {
      const search = url.searchParams.get("search")?.toLocaleLowerCase() ?? "";
      const tagId = url.searchParams.get("tag_id");
      return json(
        projects
          .filter((project) =>
            project.title.toLocaleLowerCase().includes(search),
          )
          .filter(
            (project) => !tagId || project.tags.some((tag) => tag.id === tagId),
          )
          .map(projectResponse),
      );
    }
    if (method === "GET" && path === "/document-tags") {
      refreshCounts();
      return json(tags.map((tag) => ({ ...tag })));
    }
    if (method === "POST" && path === "/document-projects") {
      const body = parseObjectBody(init);
      requireKeys(body, ["title"], ["title"]);
      const project: DocumentProject = {
        id: `11111111-1111-4111-8111-${String(nextId++).padStart(12, "0")}`,
        title: (body.title as string).trim(),
        tags: [],
        created_at: now,
        updated_at: now,
      };
      projects = [project, ...projects];
      return json(projectResponse(project), 201);
    }
    if (method === "POST" && path === "/document-tags") {
      const body = parseObjectBody(init);
      requireKeys(body, ["name", "color"], ["name", "color"]);
      const tag: DocumentTag = {
        id: `22222222-2222-4222-8222-${String(nextId++).padStart(12, "0")}`,
        name: (body.name as string).trim(),
        color: body.color as string,
        project_count: 0,
        created_at: now,
        updated_at: now,
      };
      tags = [...tags, tag];
      return json({ ...tag }, 201);
    }

    const projectMatch = path.match(/^\/document-projects\/([^/]+)$/);
    if (projectMatch) {
      const index = projects.findIndex(
        (project) => project.id === projectMatch[1],
      );
      if (index < 0)
        return json({ message: "Document project not found." }, 404);
      if (method === "GET") return json(projectResponse(projects[index]));
      if (method === "PATCH") {
        const body = parseObjectBody(init);
        requireKeys(body, ["title"], ["title"]);
        projects[index] = {
          ...projects[index],
          title: (body.title as string).trim(),
          updated_at: now,
        };
        return json(projectResponse(projects[index]));
      }
      if (method === "DELETE") {
        projects.splice(index, 1);
        refreshCounts();
        return new Response(null, { status: 204 });
      }
    }

    const tagMatch = path.match(/^\/document-tags\/([^/]+)$/);
    if (tagMatch) {
      const index = tags.findIndex((tag) => tag.id === tagMatch[1]);
      if (index < 0) return json({ message: "Document tag not found." }, 404);
      if (method === "PATCH") {
        const body = parseObjectBody(init);
        requireKeys(body, ["name", "color"]);
        const summary: DocumentTagSummary = {
          id: tags[index].id,
          name:
            typeof body.name === "string" ? body.name.trim() : tags[index].name,
          color:
            typeof body.color === "string" ? body.color : tags[index].color,
        };
        tags[index] = { ...tags[index], ...summary, updated_at: now };
        projects = projects.map((project) => ({
          ...project,
          tags: project.tags.map((tag) =>
            tag.id === summary.id ? { ...summary } : tag,
          ),
        }));
        return json({ ...tags[index] });
      }
      if (method === "DELETE") {
        tags.splice(index, 1);
        projects = projects.map((project) => ({
          ...project,
          tags: project.tags.filter((tag) => tag.id !== tagMatch[1]),
        }));
        return new Response(null, { status: 204 });
      }
    }

    const assignmentMatch = path.match(
      /^\/document-projects\/([^/]+)\/tags\/([^/]+)$/,
    );
    if (assignmentMatch && (method === "PUT" || method === "DELETE")) {
      const project = projects.find((item) => item.id === assignmentMatch[1]);
      const tag = tags.find((item) => item.id === assignmentMatch[2]);
      if (!project || !tag)
        return json({ message: "Document item not found." }, 404);
      const summary = { id: tag.id, name: tag.name, color: tag.color };
      project.tags =
        method === "PUT"
          ? [
              ...project.tags.filter((assigned) => assigned.id !== tag.id),
              summary,
            ]
          : project.tags.filter((assigned) => assigned.id !== tag.id);
      project.updated_at = now;
      refreshCounts();
      return json(projectResponse(project));
    }

    throw new Error(
      `Unexpected Documents request: ${method} ${path}${url.search}`,
    );
  }

  return {
    fetch,
    requests,
    snapshot: () => ({
      projects: projects.map(copyProject),
      tags: tags.map((tag) => ({ ...tag })),
    }),
  };
}
