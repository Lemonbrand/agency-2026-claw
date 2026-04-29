.PHONY: bootstrap demo presentation demo-agentic hackathon hackathon-offline hackathon-agentic onboard plan run-plan run correlate verify disconfirm resolve review promote ui execution-proof public-export judge-backend judge-app-init judge-refresh neotoma-smoke test

bootstrap:
	./scripts/bootstrap.sh

demo:
	./scripts/create-demo-data.py
	./bin/agency onboard
	./bin/agency plan --brain heuristic
	./bin/agency run-plan
	./bin/agency verify
	./bin/agency disconfirm --brain heuristic
	./bin/agency resolve-entities --brain heuristic
	./bin/agency correlate
	./bin/agency review --reviewer heuristic
	./bin/agency promote
	./bin/agency ui

presentation: demo

demo-agentic:
	./bin/agency onboard
	./bin/agency plan --brain codex
	./bin/agency run-plan
	./bin/agency verify
	./bin/agency disconfirm --brain codex
	./bin/agency resolve-entities --brain codex
	./bin/agency correlate
	./bin/agency review --reviewer claude
	./bin/agency promote
	./bin/agency ui

hackathon:
	./bin/agency hackathon-onboard
	./bin/agency plan --brain heuristic
	./bin/agency run-plan
	./bin/agency verify
	./bin/agency disconfirm --brain heuristic
	./bin/agency resolve-entities --brain heuristic
	./bin/agency correlate
	./bin/agency review --reviewer heuristic
	./bin/agency promote
	./bin/agency ui

# Offline rerun against the cached DuckDB. No Postgres attach, no venue Wi-Fi.
# Promote is best-effort here so a Neotoma hiccup never blocks the dashboard.
hackathon-offline:
	./bin/agency plan --brain heuristic
	./bin/agency run-plan
	./bin/agency verify
	./bin/agency disconfirm --brain heuristic
	./bin/agency resolve-entities --brain heuristic
	./bin/agency correlate
	./bin/agency review --reviewer heuristic
	./bin/agency ui
	-./bin/agency promote

hackathon-agentic:
	./bin/agency hackathon-onboard
	./bin/agency plan --brain codex
	./bin/agency run-plan
	./bin/agency verify
	./bin/agency disconfirm --brain codex
	./bin/agency resolve-entities --brain codex
	./bin/agency correlate
	./bin/agency review --reviewer claude
	./bin/agency promote
	./bin/agency ui

onboard:
	./bin/agency onboard

plan:
	./bin/agency plan --brain heuristic

run-plan:
	./bin/agency run-plan

run:
	./bin/agency run vendor-concentration
	./bin/agency run amendment-creep
	./bin/agency run related-parties

correlate:
	./bin/agency correlate

verify:
	./bin/agency verify

disconfirm:
	./bin/agency disconfirm --brain heuristic

resolve:
	./bin/agency resolve-entities --brain heuristic

review:
	./bin/agency review --reviewer heuristic

promote:
	./bin/agency promote

ui:
	./bin/agency ui

execution-proof:
	./bin/agency execution-proof

public-export:
	./bin/agency public-export

judge-backend:
	./bin/agency judge-bundle

judge-app-init:
	./bin/agency judge-app-init

judge-refresh:
	./scripts/refresh-public-until-freeze.sh

neotoma-smoke:
	./scripts/smoke-neotoma.sh

test:
	./bin/agency doctor
