package handler

import (
	"archive/zip"
	"bytes"
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestSkillHubURL(t *testing.T) {
	for _, raw := range []string{"https://skillhub.cn/skills/alice/demo?from=search", "skillhub.cn/skills/alice/demo", "https://www.skillhub.cn/skills/alice/demo/"} {
		source, normalized, err := detectImportSource(raw)
		if err != nil || source != sourceSkillHub {
			t.Fatalf("detect %s: %v", raw, err)
		}
		owner, slug, canonical, err := parseSkillHubURL(normalized)
		if err != nil || owner != "alice" || slug != "demo" || canonical != "https://skillhub.cn/skills/alice/demo" {
			t.Fatalf("parse %s: %s %s %s %v", raw, owner, slug, canonical, err)
		}
	}
	for _, raw := range []string{"https://skillhub.cn/skills/demo", "https://skillhub.cn/skills/alice/demo/extra", "https://skillhub.cn:444/skills/alice/demo", "https://bob@skillhub.cn/skills/alice/demo", "https://skillhub.cn/skills/alice/%2Fdemo", "https://skillhub.cn/skills/../demo", "https://skillhub.cn.evil.example/skills/alice/demo"} {
		if _, _, _, err := parseSkillHubURL(raw); err == nil {
			t.Errorf("accepted %s", raw)
		}
	}
}

func TestSkillHubFetchAndRefresh(t *testing.T) {
	var archive bytes.Buffer
	zw := zip.NewWriter(&archive)
	for name, content := range map[string]string{"SKILL.md": "---\nname: demo\ndescription: original\n---\n# Demo", "references/example.md": "reference", "scripts/run.py": "print('hello')"} {
		f, err := zw.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := f.Write([]byte(content)); err != nil {
			t.Fatal(err)
		}
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	for _, scenario := range []string{"success", "wrong_publisher", "unavailable", "invalid_archive", "missing_version"} {
		t.Run(scenario, func(t *testing.T) {
			downloads := 0
			ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.Header.Get("Authorization") != "" {
					t.Error("credentials sent to SkillHub")
				}
				if r.URL.Query().Get("namespace") != "alice" {
					t.Error("publisher missing from request")
				}
				switch r.URL.Path {
				case "/skills/demo":
					if scenario == "unavailable" {
						w.WriteHeader(503)
						return
					}
					owner, version := "alice", "1.2.0"
					if scenario == "wrong_publisher" {
						owner = "bob"
					}
					if scenario == "missing_version" {
						version = ""
					}
					fmt.Fprintf(w, `{"namespace":{"handle":%q,"publicSlug":"demo"},"skill":{"slug":"demo","displayName":"Demo title"},"latestVersion":{"version":%q}}`, owner, version)
				case "/download":
					downloads++
					if r.URL.Query().Get("slug") != "demo" || r.URL.Query().Get("version") != "1.2.0" {
						t.Error("download is not pinned to requested skill and version")
					}
					if scenario == "invalid_archive" {
						_, _ = w.Write([]byte("bad archive"))
						return
					}
					_, _ = w.Write(archive.Bytes())
				default:
					t.Errorf("unexpected request %s", r.URL.Path)
					w.WriteHeader(404)
				}
			}))
			defer ts.Close()
			original := skillHubAPIBase
			skillHubAPIBase = ts.URL
			defer func() { skillHubAPIBase = original }()
			imported, err := fetchImportedSkillFromOrigin(context.Background(), ts.Client(), skillOriginRef{Type: "skillhub", SourceURL: "https://skillhub.cn/skills/alice/demo?utm=x"})
			if scenario != "success" {
				if err == nil {
					t.Fatal("expected error")
				}
				if scenario != "invalid_archive" && downloads != 0 {
					t.Fatal("download attempted after invalid metadata")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if imported.name != "Demo title" || !strings.Contains(imported.content, "# Demo") || len(imported.files) != 2 {
				t.Fatalf("incomplete import: %+v", imported)
			}
			if imported.origin["namespace"] != "alice" || imported.origin["version"] != "1.2.0" || imported.origin["source_url"] != "https://skillhub.cn/skills/alice/demo" {
				t.Fatalf("wrong provenance: %+v", imported.origin)
			}
		})
	}
}

func TestSkillHubResponseCap(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte("12345")) }))
	defer ts.Close()
	_, err := readSkillHubResponse(context.Background(), ts.Client(), ts.URL, 4)
	if !isCapError(err) {
		t.Fatalf("expected cap error, got %v", err)
	}
}
