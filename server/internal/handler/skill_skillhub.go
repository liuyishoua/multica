package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
)

var skillHubAPIBase = "https://api.skillhub.cn/api/v1"
var skillHubSegment = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)

// SkillHub names are publisher-scoped; never resolve a URL by its slug alone.
func parseSkillHubURL(raw string) (namespace, slug, canonical string, err error) {
	u, err := url.Parse(raw)
	if err != nil {
		return "", "", "", fmt.Errorf("invalid SkillHub URL")
	}
	host := strings.ToLower(u.Hostname())
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	if (u.Scheme != "https" && u.Scheme != "http") || (host != "skillhub.cn" && host != "www.skillhub.cn") || u.User != nil || u.Port() != "" || len(parts) != 3 || parts[0] != "skills" || !skillHubSegment.MatchString(parts[1]) || !skillHubSegment.MatchString(parts[2]) {
		return "", "", "", fmt.Errorf("expected a SkillHub URL: https://skillhub.cn/skills/{publisher}/{skill}")
	}
	return parts[1], parts[2], "https://skillhub.cn/skills/" + parts[1] + "/" + parts[2], nil
}

func readSkillHubResponse(ctx context.Context, client *http.Client, endpoint string, limit int64) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to reach SkillHub: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= http.StatusInternalServerError {
		return nil, fmt.Errorf("%w: SkillHub returned HTTP %d", errImportSourceUnavailable, resp.StatusCode)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("SkillHub returned HTTP %d", resp.StatusCode)
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, limit+1))
	if err != nil {
		return nil, fmt.Errorf("read SkillHub response: %w", err)
	}
	if int64(len(data)) > limit {
		return nil, fmt.Errorf("%w: SkillHub response exceeds %d bytes", errImportCapExceeded, limit)
	}
	return data, nil
}

func fetchFromSkillHub(ctx context.Context, client *http.Client, raw string) (*importedSkill, error) {
	namespace, slug, canonical, err := parseSkillHubURL(raw)
	if err != nil {
		return nil, err
	}
	query := url.Values{"namespace": {namespace}}
	data, err := readSkillHubResponse(ctx, client, skillHubAPIBase+"/skills/"+url.PathEscape(slug)+"?"+query.Encode(), maxImportFileSize)
	if err != nil {
		return nil, err
	}
	var detail struct {
		Namespace struct {
			Handle     string `json:"handle"`
			PublicSlug string `json:"publicSlug"`
		} `json:"namespace"`
		Skill struct {
			Slug        string `json:"slug"`
			DisplayName string `json:"displayName"`
			Summary     string `json:"summary"`
		} `json:"skill"`
		LatestVersion struct {
			Version string `json:"version"`
		} `json:"latestVersion"`
	}
	if err := json.Unmarshal(data, &detail); err != nil {
		return nil, fmt.Errorf("invalid SkillHub metadata: %w", err)
	}
	if detail.Namespace.Handle != namespace || detail.Namespace.PublicSlug != slug || detail.Skill.Slug != slug {
		return nil, fmt.Errorf("SkillHub publisher or skill does not match the requested URL")
	}
	if detail.LatestVersion.Version == "" {
		return nil, fmt.Errorf("SkillHub skill has no downloadable version")
	}
	query.Set("slug", slug)
	query.Set("version", detail.LatestVersion.Version)
	archive, err := readSkillHubResponse(ctx, client, skillHubAPIBase+"/download?"+query.Encode(), maxImportArchiveUploadSize)
	if err != nil {
		return nil, err
	}
	imported, err := parseSkillArchive(archive, slug+".zip")
	if err != nil {
		return nil, fmt.Errorf("invalid SkillHub archive: %w", err)
	}
	if detail.Skill.DisplayName != "" {
		imported.name = detail.Skill.DisplayName
	}
	if imported.description == "" {
		imported.description = detail.Skill.Summary
	}
	imported.origin = map[string]any{"type": "skillhub", "source_url": canonical, "namespace": namespace, "slug": slug, "version": detail.LatestVersion.Version}
	return imported, nil
}
