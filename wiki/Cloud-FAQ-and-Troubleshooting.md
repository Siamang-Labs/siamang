# FAQ & Troubleshooting

Quick answers to common questions, then fixes for the situations you are most
likely to hit. Each answer links to the page with the full story.

## FAQ

### Account & access

**How do I get an API key or use my own editor?**
Create a personal token under **Profile → API keys**, or clone the repo over HTTPS
or SSH. See [[Account & Security|Cloud-Account-and-Security]] and
[[Repository & Editing|Cloud-Repository-and-Editing]].

**I forgot my password.**
Use **Forgot password?** on the sign-in screen to get a reset link by email — steps
are in [[Account & Security|Cloud-Account-and-Security]]. If you sign in with GitHub,
there's no siamang Cloud password to reset.

**Where are the Terms of Use and Privacy Policy?**
In **Profile → Support**, and online:
[Terms of Use](https://github.com/hanelias/siamang/blob/main/docs/cloud/terms-of-use.md)
·
[Privacy Policy](https://github.com/hanelias/siamang/blob/main/docs/cloud/privacy-policy.md).

### Organizations & team

**What's the difference between a personal and a cooperative organization?**
Personal is solo; cooperative lets you invite teammates with roles. You can convert
personal → cooperative any time. See
[[Organizations & Team|Cloud-Organizations-and-Team]].

**Who can invite people, and who pays?**
In a cooperative organization, the **owner** or an **admin** invites members.
Billing is per organization and only the **owner** changes the plan.

### Projects & deployment

**Empty, Template, or Example — which should I pick?**
Start from **Example** ("Digital Life & Wellbeing 2026") for your first project — it
comes with sample data so every screen works immediately. **Template** gives a
minimal survey with two starter scripts; **Empty** is a bare scaffold. See
[[Your First Project|Cloud-Your-First-Project]].

**Where is my survey's public link?**
On the **Deployments** card once the deployment is **Live**. Respondents need no
account. See [[Deploying a Survey|Cloud-Deploying-a-Survey]].

**What's the difference between Preview and Deploy?**
**Preview** builds a staging version that does **not** collect data; **Deploy**
publishes a live survey that does.

### Data

**How do I get my data out?**
**Database → Export** to CSV, Excel, SPSS (`.sav`), Parquet, or SQLite. See
[[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]].

**Can I delete a single response?**
Yes — **Database → Delete** on the row (useful for GDPR erasure). The action is
logged in **Activity**.

### Plans

**What does Free include, and what's gated?**
Free gives 2 projects, 2 members, and 500 responses per project. Webhooks and
schedules need **Plus**; connectors, Git mirrors, and SSO need **Pro**; self-hosted
is **Corporate**. See [[Plans & Billing|Cloud-Subscription-Tiers]].

**Can I change plans during the open beta?**
Not yet. Every workspace starts on a **30-day Pro trial** with full access, and the
other plans show "Available at the official release" — nothing is charged. When the
trial ends the workspace becomes read-only (your data is preserved and exportable)
until paid plans arrive at release. See [[Plans & Billing|Cloud-Subscription-Tiers]].

## Troubleshooting

### "Upgrade required" / a button is disabled

You reached a plan limit (for example a third project on Free) or used a feature
your plan doesn't include. During the open beta your **Pro trial** gives full
access; once it ends, the workspace is limited until paid plans arrive at release.
Check **Organization settings → Billing** for your status. See
[[Plans & Billing|Cloud-Subscription-Tiers]].

### A commit failed validation

The file shows an error or warning count instead of the green **valid** badge.
Click the badge to read what's wrong, fix it, and commit again — nothing goes live
until it passes. See [[Validation and Linting|Validation-and-Linting]].

### A deployment failed or is stuck

Open the build **Logs** on the deployment card to see what failed, fix it in the
repo, then **Redeploy**. A build also can't start while another is in progress for
the same environment — wait for it to finish.

### An analysis run failed

Open the run and read its **Logs**. If a step depends on an earlier one (for
example, tables need cleaned and weighted data first), run the earlier step — or use
**Run all** to run every step in order. See
[[Analysis & Reports|Cloud-Analysis-and-Reporting]].

### I can't invite someone

Check all of these: the organization is **cooperative**, you are the **owner** or an
**admin**, the person already has a siamang Cloud account, and your plan has member
room. See [[Organizations & Team|Cloud-Organizations-and-Team]].

### Clone or push fails

For **SSH**, add your public key under **Profile → SSH keys** first. If a token
stopped working, re-copy the command from **Repository → Remotes**. See
[[Account & Security|Cloud-Account-and-Security]].

### Connectors aren't moving data

Connectors are marked **Coming soon** and don't transfer data yet. Use
**Database → Export** to get your data out in the meantime.

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Using the Web App|Cloud-Web-App]] · [[Plans & Billing|Cloud-Subscription-Tiers]] · [[siamang Cloud — Overview|Cloud-Overview]]
