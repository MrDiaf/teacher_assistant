import { afterEach, describe, expect, it, vi } from "vitest";

import { documentsApi } from "./api";
import { createFakeDocumentsProvider } from "./testing/fakeDocumentsProvider";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Documents fake provider contract", () => {
  it("implements the module API contract without accepting undeclared requests", async () => {
    const provider = createFakeDocumentsProvider();
    vi.stubGlobal("fetch", vi.fn(provider.fetch));

    const project = await documentsApi.create("Contract project");
    const tag = await documentsApi.createTag("Research", "#123456");
    expect(await documentsApi.get(project.id)).toEqual(project);

    const assigned = await documentsApi.assignTag(project.id, tag.id);
    expect(assigned.tags).toEqual([
      { id: tag.id, name: "Research", color: "#123456" },
    ]);
    expect(await documentsApi.list("contract", tag.id)).toHaveLength(1);
    expect((await documentsApi.listTags())[0].project_count).toBe(1);

    const updatedTag = await documentsApi.updateTag(tag.id, {
      name: "Teaching",
      color: "#654321",
    });
    expect(updatedTag.name).toBe("Teaching");
    expect((await documentsApi.get(project.id)).tags[0]).toMatchObject({
      name: "Teaching",
      color: "#654321",
    });

    expect((await documentsApi.unassignTag(project.id, tag.id)).tags).toEqual(
      [],
    );
    await documentsApi.deleteTag(tag.id);
    await documentsApi.delete(project.id);
    expect(provider.snapshot()).toEqual({ projects: [], tags: [] });

    await expect(
      provider.fetch("/api/v1/document-projects", {
        method: "POST",
        body: JSON.stringify({ title: "Unsafe", storage_path: "/private" }),
      }),
    ).rejects.toThrow("unknown fields: storage_path");
    await expect(provider.fetch("/api/v1/calendars")).rejects.toThrow(
      "Unexpected Documents request",
    );
  });
});
