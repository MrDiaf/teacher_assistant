import { describe, expect, it } from "vitest";

import { calendarEmbeddingClasses } from "../calendar/public";
import calendarStyles from "../calendar/styles.css?raw";
import platformStyles from "../../platform/styles.css?raw";
import sharedStyles from "../../styles.css?raw";
import coursesStyles from "./styles.css?raw";

function productionSources(modules: Record<string, unknown>): string[] {
  return Object.entries(modules as Record<string, string>)
    .filter(([path]) => !path.includes(".test."))
    .map(([, source]) => source);
}

const coursesMarkup = productionSources(
  import.meta.glob("./*.tsx", {
    query: "?raw",
    import: "default",
    eager: true,
  }),
);
const calendarMarkup = productionSources(
  import.meta.glob("../calendar/*.tsx", {
    query: "?raw",
    import: "default",
    eager: true,
  }),
);

function classesDefinedIn(stylesheet: string): Set<string> {
  return new Set(
    [...stylesheet.matchAll(/\.([a-zA-Z][\w-]*)/g)].map((match) => match[1]),
  );
}

function classesRenderedBy(source: string): string[] {
  // In a template literal, only its static text and the string literals inside
  // `${...}` are class names; the expressions themselves are not.
  const literalsOnly = (template: string) =>
    template.replace(/\$\{([^}]*)\}/g, (_, expression: string) =>
      [...expression.matchAll(/"([^"]*)"/g)].map((match) => match[1]).join(" "),
    );
  return [
    ...source.matchAll(/className=(?:"([^"]*)"|\{`((?:[^`])*)`\})/g),
  ].flatMap(
    (match) =>
      (match[1] ?? literalsOnly(match[2])).match(/[a-zA-Z][\w-]*/g) ?? [],
  );
}

describe("Courses use of Calendar styling", () => {
  // A Calendar hook is a class Calendar styles or renders in its own markup.
  const calendarClasses = new Set([
    ...classesDefinedIn(calendarStyles),
    ...calendarMarkup.flatMap(classesRenderedBy),
  ]);
  const published = new Set<string>(calendarEmbeddingClasses);

  it("Calendar still styles or renders every class it publishes", () => {
    expect(
      calendarEmbeddingClasses.filter((name) => !calendarClasses.has(name)),
    ).toEqual([]);
  });

  it("Courses relies only on Calendar classes that Calendar publishes", () => {
    // A class defined by Courses itself or by the shared sheets is not a
    // dependency on Calendar, even when Calendar happens to define it too.
    const ownedElsewhere = new Set([
      ...classesDefinedIn(coursesStyles),
      ...classesDefinedIn(platformStyles),
      ...classesDefinedIn(sharedStyles),
    ]);
    const referenced = new Set([
      ...classesDefinedIn(coursesStyles),
      ...coursesMarkup.flatMap(classesRenderedBy),
    ]);
    const calendarOnly = (name: string) =>
      calendarClasses.has(name) &&
      (!ownedElsewhere.has(name) ||
        /^(calendar|embedded-calendar)-/.test(name));

    const unpublished = [...referenced]
      .filter(calendarOnly)
      .filter((name) => !published.has(name))
      .sort();

    expect(unpublished).toEqual([]);
  });
});
