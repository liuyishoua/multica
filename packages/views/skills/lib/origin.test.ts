// @vitest-environment node
import { describe, expect, it } from "vitest";
import { originSourceUrl, isRefreshableOrigin, readOrigin, type OriginInfo } from "./origin";

// `origin` is persisted JSONB writable verbatim through the skill update API,
// so originSourceUrl is the only thing standing between a hand-edited
// source_url and a live href. These tests pin the fail-closed behaviour.
describe("originSourceUrl", () => {
  const github = (source_url?: string): OriginInfo => ({
    type: "github",
    source_url,
  });

  it("accepts a source_url on the declared origin's own host", () => {
    const url = "https://github.com/anthropics/skills/tree/main/animations";
    expect(originSourceUrl(github(url))).toBe(url);
    expect(
      originSourceUrl({ type: "skills_sh", source_url: "https://skills.sh/a/b/c" }),
    ).toBe("https://skills.sh/a/b/c");
    expect(
      originSourceUrl({ type: "clawhub", source_url: "https://clawhub.ai/owner/slug" }),
    ).toBe("https://clawhub.ai/owner/slug");
  });

  it("accepts http and www variants, matching the server allowlist", () => {
    expect(originSourceUrl(github("http://www.github.com/a/b"))).toBe(
      "http://www.github.com/a/b",
    );
    expect(originSourceUrl(github("https://WWW.GITHUB.COM/a/b"))).toBe(
      "https://WWW.GITHUB.COM/a/b",
    );
  });

  it("rejects a host that does not match the declared origin type", () => {
    expect(originSourceUrl(github("https://evil.example/anthropics/skills"))).toBeNull();
    expect(originSourceUrl(github("https://skills.sh/a/b/c"))).toBeNull();
    expect(
      originSourceUrl({ type: "clawhub", source_url: "https://github.com/a/b" }),
    ).toBeNull();
    // Lookalike hosts must not pass a substring/suffix check.
    expect(originSourceUrl(github("https://github.com.evil.example/a/b"))).toBeNull();
    expect(originSourceUrl(github("https://notgithub.com/a/b"))).toBeNull();
  });

  it("rejects non-http(s) schemes", () => {
    expect(originSourceUrl(github("data:text/html,<script>x</script>"))).toBeNull();
    expect(originSourceUrl(github("javascript:alert(1)"))).toBeNull();
    expect(originSourceUrl(github("ftp://github.com/a/b"))).toBeNull();
  });

  it("rejects malformed and scheme-less values", () => {
    expect(originSourceUrl(github("not a url"))).toBeNull();
    expect(originSourceUrl(github("github.com/a/b"))).toBeNull();
    // A bare ClawHub slug is server-refreshable but not linkable.
    expect(originSourceUrl({ type: "clawhub", source_url: "my-skill" })).toBeNull();
  });

  it("rejects non-import origins even with a well-formed URL", () => {
    expect(
      originSourceUrl({ type: "manual", source_url: "https://github.com/a/b" }),
    ).toBeNull();
    expect(
      originSourceUrl({ type: "runtime_local", source_url: "https://github.com/a/b" }),
    ).toBeNull();
  });

  it("returns null for a missing or empty source_url", () => {
    expect(originSourceUrl(null)).toBeNull();
    expect(originSourceUrl(github(undefined))).toBeNull();
    expect(originSourceUrl(github(""))).toBeNull();
  });
});

// SkillHub imports retain their publisher in the source URL.
describe("SkillHub origin", () => {
  it("supports source links and refresh for publisher-scoped imports", () => {
    const origin: OriginInfo = { type: "skillhub", source_url: "https://skillhub.cn/skills/alice/demo" };
    expect(readOrigin({ config: { origin } } as Parameters<typeof readOrigin>[0])).toEqual(origin);
    expect(originSourceUrl(origin)).toBe(origin.source_url);
    expect(isRefreshableOrigin(origin)).toBe(true);
    expect(originSourceUrl({ ...origin, source_url: "https://skillhub.cn.evil.example/skills/alice/demo" })).toBeNull();
  });
});
