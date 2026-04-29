.PHONY: bootstrap demo onboard run correlate verify promote ui neotoma-smoke test

bootstrap:
	./scripts/bootstrap.sh

demo:
	./scripts/create-demo-data.py
	./bin/agency onboard
	./bin/agency run vendor-concentration
	./bin/agency run amendment-creep
	./bin/agency run related-parties
	./bin/agency correlate
	./bin/agency verify
	./bin/agency promote
	./bin/agency ui

onboard:
	./bin/agency onboard

run:
	./bin/agency run vendor-concentration
	./bin/agency run amendment-creep
	./bin/agency run related-parties

correlate:
	./bin/agency correlate

verify:
	./bin/agency verify

promote:
	./bin/agency promote

ui:
	./bin/agency ui

neotoma-smoke:
	./scripts/smoke-neotoma.sh

test:
	./bin/agency doctor
