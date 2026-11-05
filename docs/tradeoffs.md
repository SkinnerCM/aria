# Trade-offs

This page lists the main design choices in Aria, the simpler alternatives that were considered, and why they were rejected.

## Local instead of hosted

Aria runs on your own computer, alongside the projects it works on. The alternative would be a hosted service that keeps a copy of your code on its own machines. A hosted service is easier to try, because it only needs a browser tab, but it means handing your code to someone else. Aria keeps your project on your machine, and sends an AI service only what it needs for each request. The cost is that you have to install and run a real program rather than open a website.

## A separate copy for most tasks, the live files for a few

A single shared working copy uses less disk space and avoids merging. It is also how two tasks end up overwriting each other's work. Isolated tasks accept the extra disk space and the merge step so that they can run side by side. See [Isolation](isolation.md).

Not every task belongs in a separate copy, though. Some work has to change the live files directly, so Aria also supports in-place tasks, and it allows only one of them per folder at a time. Having two rules is more complex than having one, but any single rule would be wrong for one of the two cases.

## A person approves every merge

Letting each worker merge its own changes would finish tasks without any interruption. It would also let a wrong change land without anyone noticing. In addition, because all the copies share one `.git` directory, a worker running git commands could damage the main project. So an isolated worker is not allowed to run git: git is removed from its environment, Aria makes the commits itself, and Aria merges only after you accept the work. The cost is one manual step at the end of each task, and that step is intentional. You stay in control of what ships.

## One interface for every coding worker

Building Aria around a single coding assistant would have meant less code. It would also have tied Aria to that one assistant's outages and limitations. Instead, every coding worker is used through the same interface. Before work starts, that interface answers two questions: is the program installed, and is it logged in? If both answers are yes, the worker is started and given the one folder it is allowed to change.

If the program is missing or not logged in, Aria reports the problem immediately, instead of starting a worker that silently hangs while it waits for a login nobody can see.

The cost is that each coding assistant needs its own adapter. The adapters are private. The interface is included in this repository as a sample.

## What was deliberately left out

Collaboration mode, long-term memory, and memory distillation are named in the README but are not described in these documents. That is a deliberate choice: they are the features that most set Aria apart, and their design is private.
