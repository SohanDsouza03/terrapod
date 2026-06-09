package terrapod

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newPlanSummaryFixture returns a client wired to a server that records
// the last requested path so tests can assert id normalisation, and
// serves a "ready" plan_summary with two risk factors.
func newPlanSummaryFixture(t *testing.T, lastPath *string) *Client {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Body != nil {
			_, _ = io.ReadAll(r.Body)
			_ = r.Body.Close()
		}
		if lastPath != nil {
			*lastPath = r.URL.Path
		}
		w.Header().Set("Content-Type", "application/vnd.api+json")
		switch {
		case r.Method == http.MethodGet && strings.HasSuffix(r.URL.Path, "/summary"):
			_, _ = w.Write([]byte(`{"data":{"id":"plansum-aaa","type":"plan-summaries","attributes":{
			  "kind":"plan_summary","status":"ready","description":"adds one bucket",
			  "risk-level":"low","model":"bedrock/claude","input-tokens":1200,"output-tokens":340,
			  "risk-factors":[
			    {"severity":"low","title":"public bucket","detail":"acl is public-read","resource_address":"aws_s3_bucket.logs"},
			    {"severity":"info","title":"new resource","detail":"1 to add"}
			  ]
			},"relationships":{"run":{"data":{"id":"run-xyz","type":"runs"}}}}}`))
		default:
			http.Error(w, "unhandled", http.StatusNotFound)
		}
	}))
	t.Cleanup(srv.Close)
	c, err := NewClient(Options{BaseURL: srv.URL, Token: "t"})
	if err != nil {
		t.Fatal(err)
	}
	return c
}

func TestGetPlanSummary_ParsesAttributesAndRunRelationship(t *testing.T) {
	c := newPlanSummaryFixture(t, nil)
	s, err := c.GetPlanSummary(t.Context(), "plan-abc123")
	if err != nil {
		t.Fatal(err)
	}
	if s.ID != "plansum-aaa" || s.Kind != "plan_summary" || s.Status != "ready" {
		t.Errorf("summary: %+v", s)
	}
	if s.RiskLevel != "low" || s.Description != "adds one bucket" {
		t.Errorf("summary fields: %+v", s)
	}
	if s.InputTokens != 1200 || s.OutputTokens != 340 {
		t.Errorf("token telemetry: %+v", s)
	}
	// The run relationship is exposed as a bare-prefixed run id.
	if s.RunID != "run-xyz" {
		t.Errorf("run id = %q", s.RunID)
	}
	if len(s.RiskFactors) != 2 {
		t.Fatalf("risk factors: %+v", s.RiskFactors)
	}
	if s.RiskFactors[0].ResourceAddress != "aws_s3_bucket.logs" {
		t.Errorf("risk factor 0: %+v", s.RiskFactors[0])
	}
}

func TestGetPlanSummary_EmptyIDRejected(t *testing.T) {
	c := newPlanSummaryFixture(t, nil)
	if _, err := c.GetPlanSummary(t.Context(), ""); err == nil {
		t.Error("expected error for empty plan id")
	}
}

func TestGetPlanSummary_NormalisesBareUUIDToPlanPrefix(t *testing.T) {
	// Regression: a bare UUID must gain the "plan-" prefix. The old
	// length-gated check skipped this, sending /plans/<uuid>/summary.
	var path string
	c := newPlanSummaryFixture(t, &path)
	if _, err := c.GetPlanSummary(t.Context(), "abc123"); err != nil {
		t.Fatal(err)
	}
	if path != "/api/v2/plans/plan-abc123/summary" {
		t.Errorf("path = %q, want bare UUID normalised to plan- prefix", path)
	}
}

func TestGetPlanSummary_LeavesAlreadyPrefixedIDUntouched(t *testing.T) {
	var path string
	c := newPlanSummaryFixture(t, &path)
	if _, err := c.GetPlanSummary(t.Context(), "plan-abc123"); err != nil {
		t.Fatal(err)
	}
	if path != "/api/v2/plans/plan-abc123/summary" {
		t.Errorf("path = %q, want no double prefix", path)
	}
}
