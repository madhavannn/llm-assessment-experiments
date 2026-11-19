# Retrieval from scratch over the Git manuals

**Result.** With 80-word chunks, the system retrieved the annotated passage for 6 of 15 questions (40.0%). With 240-word chunks it retrieved 5 of 15 (33.3%). I would use 80 words for this particular index. The margin is one question, and the winner still misses nine.

| Chunk size | Overlap | Indexed chunks | Exact passage in top five | Recall@5 |
|---:|---:|---:|---:|---:|
| 80 words | 16 words | 2,199 | 6/15 | 40.0% |
| 240 words | 16 words | 638 | 5/15 | 33.3% |

## What was measured

The corpus consists of 36 public Git command manual pages from Git for Windows 2.56.0.windows.4. The included snapshot contains 140,129 words. The page names below link to the public manuals. Quoted passages use the bundled snapshot’s normalized whitespace. [Git manual index](https://git-scm.com/docs)

The embedding model is latent semantic analysis (LSA) implemented in NumPy. It learns which words occur in similar contexts within these manuals. Both runs use the same 96-dimensional model, fitted once on non-overlapping 100-word blocks. Sublinear term frequency and inverse document frequency weight the training matrix. A seeded truncated singular value decomposition learns the projection. Both questions and chunks pass through that fixed projection and are length-normalized. NumPy ranks every chunk by cosine similarity. The index includes the command name alongside the chunk text. Neither the questions nor the answer key enters model fitting.

Each index cuts windows independently inside each manual. Only the window length changes. Absolute overlap is fixed, so the percentage of overlap differs. A hit requires the entire annotated passage, on the annotated page, in one of the first five chunks. With one reference passage per query, recall@5 is the number of hits divided by 15. Another passage can correctly answer the question and still miss this strict metric. Answer generation is evaluated separately.

## Why chunk size changed the result

Four questions hit in both settings. The smaller windows gained Q2 and Q11, while the larger windows gained Q8. For Q2, about following a file through a rename, the short git-blame passage ranked 2nd. Its larger counterpart ranked 32nd, behind passages about how diffs display renamed files. A plausible explanation is that longer chunks mix the relevant rule with neighboring options. For Q11, both searches identified git-bundle, but the exact verification passage moved from rank 5 to rank 6. This single-position change matters at a cutoff of five.

Q8 shows the opposite effect. The first 80-word result actually included the required flag and what it does. Its window began at “unless”, omitting “Implies --single-branch” from the beginning of the gold passage. The first complete span ranked 8th. A 240-word chunk preserved the full rule at rank 2. The difference in scores therefore reflects both ranking and the choice to require a complete reference span.

## Two retrieval failures and tested fixes

| Question, 80-word index | What the run returned | What changed the outcome |
|---|---|---|
| Q3 · A nested repository survived cleanup | All five results came from git-clone. The git-clean rule about a second force flag ranked 442nd. The question mentions a repository but omits the literal command and flag. | Adding “git clean untracked nested -f” to the query moved the same passage to rank 1. An alias table could map “cleanup” to “git clean” and “force flag” to “-f”. |
| Q5 · A secondary checkout lives on a removable drive | All five results came from git-checkout. The git-worktree rule ranked 322nd. “Checkout” is a command name here, while the manual calls the secondary checkout a “linked worktree”. | Adding “linked worktree prune administrative files portable device” moved the passage to rank 1. A query rewrite could map “secondary checkout” and “USB drive” to the manual’s terms. |

These are post-run probes using terms identified from the gold passages. They show that vocabulary mattered in these cases. An automatic rewrite system would need a fresh test set to measure its benefit without using the answers.

## What BM25 and a re-ranker add

**BM25** gives exact terms their own route into the candidate list. If someone asks about the literal flag `--intent-to-add`, a passage containing that rare flag gets a strong signal. Frequent words such as “git” carry much less weight. Repetition has diminishing returns, and document-length normalization keeps a long chunk from winning simply because it contains more words. A hybrid search could merge the BM25 and embedding candidate lists. For Git manuals, its tokenizer should preserve flags. When someone calls a worktree a “secondary checkout”, BM25 alone still lacks the missing vocabulary.

**A re-ranker** reads the question alongside each shortlisted passage and scores how directly it answers that particular question. For Q11 the 240-word index already put verification instructions at rank 6. A re-ranker given the top 20 could consider that passage and promote it ahead of general bundle descriptions. For Q3 the answer was at rank 442 in the smaller index. Reordering the first 20 would never see it. BM25 and re-ranking are proposed extensions. The measured baselines use embedding retrieval only.

## Question-answering check

The ask command supplies the five retrieved excerpts to Qwen2.5-0.5B-Instruct with numbered sources and requests a brief grounded answer. The two tested baseline questions expose a generation limitation. For Q6 the decisive sentence was ranked 2nd, yet the model copied a neighboring excerpt and stopped before answering how to resolve the conflict. For Q4 it cited an unrelated git-branch passage despite retrieving the 90-day rule at rank 4. These were retrieval hits and unsuccessful generated answers. On a third probe about tags, the generator returned only a citation. An extractive mode is included for short, directly stated answers. On Q6 it returned two cited sentences that together say the entry stays in the stash list, conflicts need manual resolution, and git stash drop removes the entry afterward. This same-question example is saved in demo-extract.json. No overall answer-accuracy rate was measured.

## All 15 test questions and source passages

Ranks below count from 1 in the full index. A rank of 5 or lower is a hit.

### Q1. My automated bisect check sometimes lands on a revision that cannot build. Which exit status tells Git to skip it?

**Reference answer.** Return 125.

> The special exit code 125 should be used when the current source code cannot be tested. If the script exits with this code, the current revision will be skipped

[git-bisect manual](https://git-scm.com/docs/git-bisect) · Gold rank with 80 words **33**, with 240 words **6**.

### Q2. After someone renamed a whole file, do I need an option to trace who last edited its lines before the rename?

**Reference answer.** No. Git blame follows whole-file renames automatically.

> The origin of lines is automatically followed across whole-file renames (currently there is no option to turn the rename-following off).

[git-blame manual](https://git-scm.com/docs/git-blame) · Gold rank with 80 words **2**, with 240 words **32**.

### Q3. Why did a nested repository survive cleanup when I already supplied one force flag?

**Reference answer.** An untracked nested repository has extra protection. Removing it requires a second -f.

> Git will refuse to modify untracked nested git repositories (directories with a .git subdirectory) unless a second -f is given.

[git-clean manual](https://git-scm.com/docs/git-clean) · Gold rank with 80 words **442**, with 240 words **217**.

### Q4. What is the default age cutoff for ordinary reflog expiration when I leave the configuration alone?

**Reference answer.** 90 days.

> the expiration time is taken from the configuration setting gc.reflogExpire , which in turn defaults to 90 days.

[git-reflog manual](https://git-scm.com/docs/git-reflog) · Gold rank with 80 words **4**, with 240 words **1**.

### Q5. My secondary checkout lives on a USB drive. How do I keep Git from tidying away its bookkeeping while the drive is unplugged?

**Reference answer.** Use git worktree lock on the linked worktree.

> you can prevent its administrative files from being pruned by issuing the git worktree lock command

[git-worktree manual](https://git-scm.com/docs/git-worktree) · Gold rank with 80 words **322**, with 240 words **57**.

### Q6. My stash pop produced conflicts. Where is my saved work, and how do I remove the entry after resolving them?

**Reference answer.** The entry remains in the stash list. Resolve the conflicts and then use git stash drop.

> Applying the state can fail with conflicts; in this case, it is not removed from the stash list. You need to resolve the conflicts by hand and call git stash drop manually afterwards.

[git-stash manual](https://git-scm.com/docs/git-stash) · Gold rank with 80 words **2**, with 240 words **1**.

### Q7. A faulty change is already in shared history. Which operation records its reversal as another commit?

**Reference answer.** Use git revert.

> git revert is used to record some new commits to reverse the effect of some earlier commits

[git-revert manual](https://git-scm.com/docs/git-revert) · Gold rank with 80 words **437**, with 240 words **43**.

### Q8. I want a shallow clone of depth five, but I need the tips of every branch. What do I need in addition to the depth option?

**Reference answer.** Add --no-single-branch.

> Implies --single-branch unless --no-single-branch is given to fetch the histories near the tips of all branches.

[git-clone manual](https://git-scm.com/docs/git-clone) · Gold rank with 80 words **8**, with 240 words **2**.

### Q9. Which attribute lets me keep test fixtures in the repository while leaving them out of release archives?

**Reference answer.** Set export-ignore on those paths.

> Files and directories with the attribute export-ignore won’t be added to archive files.

[git-archive manual](https://git-scm.com/docs/git-archive) · Gold rank with 80 words **973**, with 240 words **156**.

### Q10. I made a lightweight tag. Why might git describe ignore it when I run the command without options?

**Reference answer.** By default git describe considers only annotated tags.

> By default (without --all or --tags ) git describe only shows annotated tags.

[git-describe manual](https://git-scm.com/docs/git-describe) · Gold rank with 80 words **3**, with 240 words **1**.

### Q11. Before using a bundle, how do I check that this receiving repository has the commits it depends on?

**Reference answer.** Run git bundle verify <file> in the receiving repository.

> verify <file> Used to check that a bundle file is valid and will apply cleanly to the current repository. This includes checks on the bundle format itself as well as checking that the prerequisite commits exist and are fully linked in the current repository.

[git-bundle manual](https://git-scm.com/docs/git-bundle) · Gold rank with 80 words **5**, with 240 words **6**.

### Q12. I took over someone else's change while amending it. Which flag makes me the author and refreshes the author timestamp?

**Reference answer.** Use --reset-author with --amend.

> --reset-author When used with -C / -c / --amend options, or when committing after a conflicting cherry-pick, declare that the authorship of the resulting commit now belongs to the committer. This also renews the author timestamp.

[git-commit manual](https://git-scm.com/docs/git-commit) · Gold rank with 80 words **73**, with 240 words **45**.

### Q13. While fetching, how can I discard local remote-tracking references whose counterparts were deleted upstream?

**Reference answer.** Use git fetch --prune.

> -p --prune Before fetching, remove any remote-tracking references that no longer exist on the remote.

[git-fetch manual](https://git-scm.com/docs/git-fetch) · Gold rank with 80 words **56**, with 240 words **19**.

### Q14. How can I register a new path in the index now but leave its contents unstaged for review?

**Reference answer.** Use git add -N on that path.

> -N --intent-to-add Record only the fact that the path will be added later. An entry for the path is placed in the index with no content.

[git-add manual](https://git-scm.com/docs/git-add) · Gold rank with 80 words **3**, with 240 words **1**.

### Q15. I want to attach a review comment to an existing commit without changing its object ID. What Git facility does that?

**Reference answer.** Use Git notes.

> Adds, removes, or reads notes attached to objects, without touching the objects themselves.

[git-notes manual](https://git-scm.com/docs/git-notes) · Gold rank with 80 words **895**, with 240 words **160**.
