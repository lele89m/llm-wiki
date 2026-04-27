# Customization Guide

This template ships with two pre-built wiki types: **work** (IT cloud provider) and **personal**.
If your context is different — a law firm, a research lab, a medical team, a startup — this guide
shows you exactly what to change and how.

---

## What to customize vs. what to leave alone

**Leave alone** — these are universal and work for any domain:
- Workflows (Ingest, Query, Lint)
- Confidence protocol
- Gap tracking
- Frontmatter schema
- Output formats (Marp, Dataview, matplotlib)
- Security section
- All CLI tools

**Customize for your domain:**
1. Wiki title and purpose (first line)
2. Directory structure (categories)
3. Domain context (last section)
4. Page types (optional — only if your domain needs new ones)
5. `setup.sh` directory creation

---

## Step-by-step

### Step 1 — Fork the wiki type that's closest

Copy `templates/work/CLAUDE.md` or `templates/personal/CLAUDE.md` as your starting point.
Work wikis are better for team/organizational knowledge. Personal wikis are better for
individual research and note-taking.

### Step 2 — Change the title and purpose

```markdown
# Wiki Schema — [YOUR CONTEXT HERE]

You are the maintainer of this wiki. The human curates sources and asks questions.
You write and maintain all wiki pages. Never modify files in `raw/` — that is the source of truth.
```

Change `[YOUR CONTEXT HERE]` to something specific:
- `Legal Knowledge Base — Contract Law`
- `Research Wiki — Climate Science`
- `Product Wiki — SaaS Startup`

### Step 3 — Replace the directory structure

The categories define what your wiki covers. Replace the `wiki/` section with your own:

```
wiki/
  index.md
  log.md
  overview.md
  gaps.md
  _templates/
  [your-category-1]/
  [your-category-2]/
  ...
  sources/
  analysis/
```

Keep `sources/` and `analysis/` — they are used by the workflows.
Everything else is yours to define.

### Step 4 — Replace the domain context section

This is the most important section. It tells the LLM what domain knowledge to apply,
what terminology is standard, and what to create pages for proactively.

Find the section at the bottom of CLAUDE.md:
```markdown
## Domain context — IT cloud provider
...
```

Replace it entirely with your own. See the examples below.

### Step 5 — Update setup.sh

In `setup.sh`, find the `create_dirs()` function and update the category directories
to match your new structure:

```bash
# find this block and replace the categories:
if [[ "$WIKI_TYPE" == "work" ]]; then
  mkdir -p "$TARGET_DIR/wiki"/{your-cat-1,your-cat-2,your-cat-3,sources,analysis}
```

---

## Examples

### Example A — Law firm / legal team

**Directory structure:**
```
wiki/
  matters/       ← active cases and client matters
  contracts/     ← contract types, clauses, templates
  precedents/    ← case law and judicial decisions
  regulations/   ← statutes, regulations, compliance requirements
  clients/       ← client profiles
  jurisdictions/ ← country and regional law summaries
  concepts/      ← legal concepts and definitions
  sources/
  analysis/
```

**Domain context section:**
```markdown
## Domain context — Legal

This wiki serves a legal team. Key domain areas:

**Practice areas**
- Contract law: drafting, negotiation, interpretation, breach
- Corporate law: M&A, governance, shareholder agreements
- Compliance: GDPR, sector-specific regulations, internal policies
- Litigation: case strategy, precedents, procedural rules

**Terminology**
- Matter: a specific client engagement or case
- Precedent: prior case law that influences current decisions
- Jurisdiction: the legal system that applies (country, state, EU, etc.)
- Clause: a specific provision within a contract

**Time-sensitive pages** — set `valid_until` for:
- Regulatory deadlines and filing dates
- Case hearing dates
- Contract expiry dates
- Compliance review dates

When you encounter unfamiliar legal terms, create concept pages proactively.
Cross-reference matters with the relevant regulations and precedents.
```

---

### Example B — Medical / clinical team

**Directory structure:**
```
wiki/
  protocols/     ← clinical protocols and treatment guidelines
  conditions/    ← disease and condition reference pages
  medications/   ← drug reference, interactions, dosages
  procedures/    ← surgical and diagnostic procedures
  research/      ← studies, trials, evidence summaries
  departments/   ← team structure and specializations
  concepts/      ← medical and scientific concepts
  sources/
  analysis/
```

**Domain context section:**
```markdown
## Domain context — Clinical / Medical

This wiki serves a clinical team. Key domain areas:

**Clinical knowledge**
- Treatment protocols and evidence-based guidelines
- Drug interactions, contraindications, dosage ranges
- Diagnostic criteria and differential diagnosis
- Surgical and interventional procedures

**Research**
- Clinical trial summaries: RCTs, meta-analyses, systematic reviews
- Evidence levels: Level I (RCT) → Level V (expert opinion)
- Key journals: NEJM, Lancet, JAMA, BMJ

**Terminology**
- Protocol: a standardized treatment or diagnostic procedure
- Contraindication: a condition that makes a treatment inadvisable
- NNT/NNH: number needed to treat / number needed to harm
- Comorbidity: co-existing medical conditions

**Time-sensitive pages** — set `valid_until` for:
- Drug approval dates and formulary updates
- Guideline revision dates (guidelines are updated periodically)
- Trial follow-up deadlines

⚠️ This wiki is for reference only. Always verify clinical decisions
against current official guidelines before acting.
```

---

### Example C — Software startup / product team

**Directory structure:**
```
wiki/
  product/       ← features, roadmap, product decisions
  engineering/   ← architecture, technical decisions, systems
  customers/     ← customer profiles, segments, feedback
  operations/    ← processes, runbooks, on-call
  growth/        ← metrics, experiments, marketing
  competitors/   ← competitive analysis
  decisions/     ← product and technical ADRs
  concepts/      ← domain concepts
  sources/
  analysis/
```

**Domain context section:**
```markdown
## Domain context — SaaS Startup

This wiki serves a product and engineering team building a SaaS product.
Key domain areas:

**Product**
- Feature specifications and acceptance criteria
- User personas and jobs-to-be-done
- Roadmap decisions and prioritization rationale
- A/B test results and experiments

**Engineering**
- System architecture and data flow
- API design and integration patterns
- Performance benchmarks and SLOs
- Incident post-mortems and runbooks

**Growth**
- Key metrics: MRR, churn, CAC, LTV, NPS
- Conversion funnel and activation milestones
- Customer segments and ICP (Ideal Customer Profile)

**Terminology**
- ICP: Ideal Customer Profile
- PLG: Product-Led Growth
- SLO/SLA: Service Level Objective / Agreement
- Churn: rate at which customers cancel

**Time-sensitive pages** — set `valid_until` for:
- Roadmap items with committed dates
- Experiment results (decisions should be revisited)
- Pricing and packaging (changes frequently)
- Competitor analysis (stale quickly)
```

---

### Example D — Research / academic

**Directory structure:**
```
wiki/
  papers/        ← paper summaries and critiques
  authors/       ← researcher profiles and their contributions
  concepts/      ← theoretical concepts and models
  methods/       ← research methods and statistical approaches
  datasets/      ← dataset descriptions and provenance
  debates/       ← open questions and competing theories
  timeline/      ← chronological development of the field
  sources/
  analysis/
```

**Domain context section:**
```markdown
## Domain context — Research (replace with your field)

This wiki supports deep research on [FIELD]. Key areas:

**Literature**
- Papers are the primary source type
- Track: publication date, journal/venue, citation count, methodology
- Note replication status where known (replicated / failed / contested)

**Evidence quality**
- Distinguish: empirical finding vs. theoretical claim vs. speculation
- Flag when a claim rests on a single study
- Note sample sizes and effect sizes when relevant

**Concepts**
- Create a page for every named concept, model, or framework encountered
- Note who coined it, when, and how the definition has evolved
- Cross-reference competing or complementary concepts

**Debates**
- When sources disagree, create a `debates/` page that maps both sides
- Cite specific papers on each side, note the state of consensus

**Time-sensitive pages** — set `valid_until` for:
- Preprints awaiting peer review
- Claims based on preliminary data
- Your own synthesis pages (revisit after reading 10+ more papers)
```

---

## Quick checklist

Before running `bash setup.sh` with your custom template:

- [ ] Title changed to your context
- [ ] Directory categories reflect your domain
- [ ] Domain context section replaced (bottom of CLAUDE.md)
- [ ] `setup.sh` `create_dirs()` updated with your categories
- [ ] `AGENTS.md` is a copy of your updated `CLAUDE.md` (setup.sh does this automatically)

The workflows, tools, and confidence protocol require no changes — they work for any domain.
