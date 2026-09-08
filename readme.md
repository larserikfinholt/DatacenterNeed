# Project: Measuring the Real Societal Need for Data Centres

> **Important:** All current NO/SE fixture numbers are synthetic. They are not empirical national estimates. There is no web dashboard or real dataset yet; `national_total` remains `null`.

## Quickstart

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```powershell
uv sync --frozen
uv run datacenter-need validate --input data/examples/synthetic.yaml
uv run datacenter-need build --offline --input data/examples/synthetic.yaml --output build/example
uv run pytest
uv run ruff check .
```

The offline build writes replayable input traces and artifacts to `build/example/`: `result.json`, `occupation_breakdown.csv`, `input.schema.json`, and `manifest.json`. Schema export is optional:

```powershell
uv run datacenter-need schema --output build/input.schema.json
```

Read the [methodology](docs/methodology.md), [source register](docs/source-register.md), [contribution guidance](CONTRIBUTING.md), and [implementation status](docs/implementation-status.md) before interpreting or extending the fixtures.

## Purpose

Build an open, evidence-based project for assessing how much data-centre capacity societies actually need, what that capacity is used for, and what societal value is created in return for the energy, land, grid capacity and infrastructure consumed.

The project starts with Norway, but must be designed conceptually for multiple countries. The ambition is that researchers, developers, energy experts, public-sector employees and others can contribute data, assumptions and corrections over time.

The project should not start from the assumption that data centres are either good or bad.

Its purpose is to make the underlying assumptions visible and testable.

A central hypothesis to investigate is that projected data-centre demand, particularly demand attributed to AI and "digital transformation", may be substantially larger than the compute actually required to create useful societal outcomes.

At the same time, the project must actively look for evidence that disproves this hypothesis.

## Background

Public debate around data centres often includes claims such as:

* AI will transform almost every occupation.
* Companies that do not adopt AI rapidly will become uncompetitive.
* Digital transformation requires large increases in compute capacity.
* AI will automate large parts of the economy.
* Data centres are necessary infrastructure for future jobs and economic growth.
* Countries need domestic AI infrastructure to remain competitive.
* Large data centres create jobs, tax revenue and local economic activity.

These claims should be measurable rather than accepted at face value.

Many occupations may have relatively modest compute requirements.

Nurses, care workers, teachers, construction workers, electricians, mechanics, police officers, firefighters and many other workers spend much of their working day interacting with people or the physical world rather than computers.

AI may still improve parts of these jobs, but this could amount to occasional inference requests, documentation assistance, search, planning or administrative automation rather than continuous intensive computation.

Even knowledge workers may have highly uneven AI demand.

Developers, lawyers, consultants, engineers and analysts may use powerful AI systems, but organizational processes, decisions, integration work, regulation, human review and change management may become more important bottlenecks than model capability.

Increasing model capability therefore does not necessarily translate linearly into increasing societal productivity.

At the same time, smaller and local models are becoming increasingly capable. Some AI workloads may migrate from centralized data centres to laptops, workstations, phones, vehicles, industrial equipment and other edge devices.

The project should investigate how these effects influence the actual need for centralized compute.

## Core questions

The project should help answer:

### How much AI compute do people actually need?

For each major occupation or occupational group:

* How many people work in the occupation?
* How much of their working time involves digital systems?
* How much of that digital activity could realistically involve AI?
* How frequently would AI be used?
* What kinds of AI tasks are involved?
* How computationally demanding are those tasks?
* Does the task require a frontier model, a smaller cloud model or a local model?

The aim is to estimate realistic AI compute demand per worker and aggregate this across the economy.

### Which occupations actually require substantial AI compute?

Compare occupations such as:

* healthcare workers
* teachers
* care workers
* tradespeople
* industrial workers
* transport workers
* police and emergency services
* public administration
* lawyers
* consultants
* engineers
* researchers
* developers
* media and creative workers

Avoid assuming that "AI adoption" means constant AI use.

Separate occasional assistance from continuous AI workloads.

### How much AI can run locally?

Investigate the increasing capability of:

* laptop GPUs
* NPUs
* desktop GPUs
* mobile devices
* industrial edge hardware
* smaller open-weight models

Estimate which classes of AI workloads genuinely require centralized data centres and which could reasonably run locally.

The project should track how this changes over time.

### When are frontier models actually necessary?

Investigate where very large models provide meaningful additional value compared with smaller models.

Examples may include:

* complex software engineering
* scientific reasoning
* large-document analysis
* advanced research
* autonomous agents
* multimodal processing

Contrast this with simpler workloads such as:

* classification
* extraction
* summarisation
* translation
* form assistance
* simple document generation
* search assistance
* workflow routing

Estimate how much AI usage falls into each category.

### How much compute is required for AI inference?

Estimate energy and compute requirements based on realistic usage scenarios.

The project should be able to reason from:

people → working hours → digital activity → AI activity → requests → tokens → models → compute → electricity.

The goal is not false precision, but transparent assumptions.

### How important is model training?

Separate:

* foundation-model training
* model fine-tuning
* specialist model training
* RAG and retrieval
* inference

Investigate how often normal companies actually need to train their own models.

Many organizations may have insufficient proprietary data or insufficient reason to train a model and instead use existing models, RAG, prompting or small fine-tuning jobs.

Quantify this where evidence exists.

### How much data-centre capacity is actually related to AI?

Data centres support much more than generative AI.

Separate demand from:

* traditional cloud workloads
* SaaS
* databases
* storage
* backup
* video
* web services
* search
* HPC
* telecommunications
* AI inference
* AI training
* cryptocurrency where relevant
* other specialized workloads

Avoid attributing all future data-centre growth to AI.

### Does AI usage in a country require data centres in that country?

Distinguish between:

* national digital demand
* domestic data-centre capacity
* exported compute
* imported cloud services
* hyperscale infrastructure serving several countries
* sovereignty requirements
* latency requirements
* resilience and redundancy requirements

A country could consume significant AI services without hosting the corresponding compute locally.

Likewise, a country could host enormous data centres whose output is primarily consumed elsewhere.

These are fundamentally different questions.

### How much electricity do existing and proposed data centres require?

For each country, compare:

* existing capacity
* capacity under construction
* approved projects
* proposed projects
* grid connection requests
* reserved grid capacity
* estimated actual utilization
* electricity consumption

Clearly distinguish between:

* MW connection capacity
* MW actual load
* annual MWh/TWh
* IT load
* total facility load
* PUE
* peak demand

### What is the societal value produced?

Compare resource consumption against measurable outcomes such as:

* direct permanent employment
* construction employment
* tax revenue
* local economic activity
* national value creation
* export revenue
* research capability
* strategic autonomy
* infrastructure resilience

Avoid treating construction jobs and permanent jobs as equivalent.

Where possible, calculate indicators such as:

* MW per permanent job
* GWh per permanent job
* GWh per unit of value creation
* tax revenue per MW
* land use per MW
* public infrastructure investment per permanent job

### How much productivity does AI actually create?

Distinguish between:

task productivity

and

organizational or societal productivity.

An AI system may make one task 50% faster without making the organization 50% more productive.

Investigate constraints such as:

* human approval
* organizational processes
* regulation
* integration
* procurement
* customer decisions
* physical work
* coordination
* management
* change capacity

The project should examine empirical evidence rather than extrapolating benchmark improvements directly to GDP growth.

### Could increased efficiency actually increase compute demand?

Include rebound effects.

Cheaper and more capable AI could cause people to use much more AI.

Questions include:

* If inference becomes 10× cheaper, will usage increase 10×?
* Will AI agents run continuously rather than interactively?
* Will synthetic content dramatically increase workload?
* Will software increasingly contain thousands of autonomous AI processes?
* Could local AI stimulate additional cloud AI usage rather than replace it?

This is one of the strongest challenges to the project's central hypothesis and should be treated seriously.

## Scenarios

The project should allow comparison of different futures rather than producing a single forecast.

At minimum consider:

### Conservative AI adoption

AI improves selected tasks but most jobs remain dominated by human and physical activity.

AI usage is intermittent.

Small and local models handle many tasks.

### Moderate adoption

AI assistants become common across most knowledge work and administration.

AI becomes embedded in many business processes.

Cloud inference grows substantially.

### High adoption

AI agents perform large amounts of continuous autonomous work.

Software systems generate much larger inference volumes than human interaction alone would suggest.

Frontier-model usage remains important.

### Local AI scenario

A significant share of inference moves to PCs, phones, vehicles and industrial devices.

### Centralized AI scenario

Cloud economics and rapidly improving frontier models keep most AI workloads in large data centres.

These scenarios should make disagreements about assumptions visible rather than hiding them inside a single model.

## Country comparison

Norway should be the first dataset.

The project should later support comparisons between countries.

Relevant country-level dimensions include:

* population
* workforce
* occupations
* GDP
* electricity production
* electricity consumption
* electricity prices
* grid constraints
* renewable generation
* data-centre capacity
* proposed data-centre projects
* AI adoption
* cloud adoption
* industrial structure
* climate
* taxation
* data sovereignty requirements

This should make it possible to ask questions such as:

"Does Norway need 2 GW of additional data-centre capacity to support Norwegian digitalization?"

or:

"What level of domestic AI activity would be required to consume 2 GW continuously?"

or:

"How many AI inference requests per worker would correspond to the capacity of a proposed data centre?"

These kinds of comparisons should turn abstract infrastructure numbers into understandable quantities.

## Data

The project should favour authoritative, reproducible sources.

For Norway, relevant sources are likely to include:

* Statistics Norway / SSB
* Statnett
* NVE
* RME
* Nkom
* Digitaliseringsdirektoratet
* government ministries
* municipalities
* planning documents
* company announcements and filings

International sources may include:

* IEA
* Eurostat
* OECD
* EU/JRC
* national statistical agencies
* energy regulators
* grid operators
* academic research
* Stanford AI Index
* Anthropic Economic Index
* OpenAI economic research
* METR
* Uptime Institute
* Lawrence Berkeley National Laboratory
* US Department of Energy
* EPRI

Commercial or vendor-funded research can be included, but should be clearly identified as such.

Every important number should ideally include:

* source
* date
* geography
* definition
* unit
* assumptions
* uncertainty

Contributors should be able to add better data or challenge assumptions.

## Dashboard

The project should include a deliberately simple public dashboard presenting the collected data and calculated scenarios.

The dashboard should make it possible to explore questions rather than simply present a predetermined conclusion.

Useful views could include:

* existing and planned data-centre capacity by country
* data-centre electricity demand
* national electricity consumption
* employment by occupation
* estimated digital working time
* estimated AI usage by occupation
* estimated AI inference energy demand
* local versus cloud inference
* training versus inference
* conservative/moderate/high AI scenarios
* AI demand versus planned data-centre capacity
* permanent jobs versus MW
* electricity use versus estimated value creation
* announced capacity versus estimated actual utilization

Simple charts and tables are sufficient.

The important requirement is that every visualization can be traced back to its source data and assumptions.

## Principles

The project should be:

**Evidence-based**

Claims should be supported by data where possible.

**Falsifiable**

The project must contain enough information to show that the central hypothesis is wrong if the evidence points in that direction.

**Transparent**

Assumptions should be visible and adjustable.

**Open to contribution**

Others should be able to contribute datasets, corrections, alternative assumptions and country-specific information.

**Country-neutral**

Norway is the starting point, not a special case embedded into the conceptual model.

**Explicit about uncertainty**

Ranges are preferable to unjustified precision.

**Neutral about technology**

The project should not assume that cloud, local AI, open models or frontier models will dominate.

**Neutral about the conclusion**

The project should be equally capable of demonstrating that planned data-centre capacity is excessive or that substantially more capacity is justified.

## Ultimate question

The project should ultimately help answer:

> Given the population, economy, occupations, realistic AI usage, digital workloads and strategic requirements of a country, how much data-centre capacity is reasonably required — and what societal value does the additional capacity create relative to the electricity, grid capacity, land and other resources it consumes?

For Norway, the first objective is to determine whether currently planned growth in data-centre capacity can reasonably be explained by Norwegian societal and economic demand, or whether a substantial part of that capacity represents export-oriented compute whose costs and benefits should be evaluated as an industrial activity rather than as a prerequisite for Norwegian digital transformation.
