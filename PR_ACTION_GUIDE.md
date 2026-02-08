# Quick Action Guide for Pull Request Management

## Immediate Actions Required

### 🚨 Priority 1: Resolve Merge Conflict (PR #16)

```bash
# Step 1: Checkout the branch with conflicts
git fetch origin
git checkout copilot/update-to-pexels-api
git pull origin copilot/update-to-pexels-api

# Step 2: Merge main to get latest changes
git merge origin/main

# Step 3: Conflicts will appear - resolve them
# Open each conflicted file and look for:
# <<<<<<< HEAD
# ... your changes ...
# =======
# ... main branch changes ...
# >>>>>>> origin/main

# Step 4: After resolving all conflicts
git add .
git commit -m "Resolve merge conflicts with main"
git push origin copilot/update-to-pexels-api

# Step 5: Verify on GitHub that conflicts are resolved
```

### 📋 Priority 2: Consolidate Duplicate PRs

You have several PRs that implement similar functionality. Review and close duplicates:

#### User Management (Choose 1 of 3):
- PR #6: `copilot/add-user-management-functionality`
- PR #7: `copilot/add-user-management-features`
- PR #8: `copilot/enhance-user-management-bot`

**Recommendation**: Review each, pick the most complete implementation, close others.

#### Text Sanitization (Choose 1 of 2):
- PR #4: `copilot/fix-bot-py-text-cleanup`
- PR #5: `copilot/enhance-generate-content-function` (Draft)

**Recommendation**: If #5 is more complete, mark as ready for review and close #4.

#### Image Fetching Improvements (Choose 1 of 2):
- PR #11: `copilot/add-image-fetcher-improvements` (14 files, +1575/-76)
- PR #12: `copilot/update-image-fetcher-functionality` (10 files, +1427/-74)

**Recommendation**: PR #11 has more additions. Review both and merge the better one.

### ⚠️ Priority 3: Check Merge Status for Unknown PRs

Run this for each PR with unknown merge state:

```bash
# For PR #13
git checkout copilot/populate-api-setup
git merge origin/main --no-commit --no-ff
# Check for conflicts, then:
git merge --abort  # if just testing

# For PR #12
git checkout copilot/update-image-fetcher-functionality
git merge origin/main --no-commit --no-ff
git merge --abort

# For PR #11
git checkout copilot/add-image-fetcher-improvements
git merge origin/main --no-commit --no-ff
git merge --abort
```

## Suggested Merge Sequence

To avoid cascading conflicts, merge in this order:

1. **First**: PR #3 (Refactoring) - Creates clean foundation
2. **Second**: PR #1 (README) - Documentation only, low risk
3. **Third**: Best of User Management PRs (#6, #7, or #8)
4. **Fourth**: Best of Text Sanitization PRs (#4 or #5)
5. **Fifth**: Best of Image PRs (#11 or #12)
6. **Sixth**: PR #16 (Pexels) - After resolving conflicts
7. **Seventh**: PR #13 (Express API) - Independent feature
8. **Eighth**: PR #10 (Yandex Wordstat) - Complex feature last

## Commands Cheat Sheet

### Check PR Status Locally
```bash
# List all remote branches
git branch -r | grep copilot

# Check if branch can merge cleanly
git checkout <branch-name>
git merge origin/main --no-commit --no-ff
# If successful:
git merge --abort
# If conflicts, see them and resolve
```

### Update PR Branch
```bash
git checkout <branch-name>
git pull origin <branch-name>
git merge origin/main
# Resolve any conflicts
git push origin <branch-name>
```

### Close a PR via Command Line
```bash
# Just delete the branch after closing on GitHub
git push origin --delete <branch-name>
git branch -D <branch-name>  # local cleanup
```

## Decision Matrix for Duplicate PRs

When you have multiple PRs for the same feature:

| Criteria | Weight | What to Check |
|----------|--------|---------------|
| Code Quality | High | Clean code, good practices, comments |
| Test Coverage | High | Number and quality of tests |
| Completeness | High | All required features implemented |
| Documentation | Medium | README, inline docs, examples |
| Recent Updates | Low | Latest changes (but quality matters more) |

### Quick Comparison Commands

```bash
# Compare file changes between two branches
git diff copilot/branch-1..copilot/branch-2 -- path/to/file.py

# See list of files changed in each branch
git diff --name-only origin/main..copilot/branch-1
git diff --name-only origin/main..copilot/branch-2

# Count lines changed
git diff --stat origin/main..copilot/branch-1
```

## Testing Before Merge

For each PR before merging:

```bash
# 1. Checkout the PR branch
git checkout <branch-name>

# 2. Install/update dependencies
pip install -r requirements.txt
# or for Node.js PRs:
cd api && npm install

# 3. Run tests
python -m pytest  # if tests exist
# or
python test_*.py

# 4. Manual testing
# - Start the bot
# - Test the specific feature
# - Check for errors in logs
```

## Final Checklist Before Merging

- [ ] No merge conflicts
- [ ] All tests pass
- [ ] Code review completed
- [ ] Documentation updated
- [ ] No security vulnerabilities (run `pip-audit` or `safety check` after installing)
- [ ] Feature tested manually
- [ ] Related PRs identified (duplicates, conflicts)

## After Merging

```bash
# 1. Delete the merged branch
git push origin --delete <branch-name>
git branch -D <branch-name>

# 2. Update your local main
git checkout main
git pull origin main

# 3. Check if any other PRs now have conflicts
# (GitHub will show this automatically)
```

## После мерджа

Краткий чеклист действий после успешного слияния PR:

- [ ] **Удалить смерженную ветку**: `git push origin --delete <branch-name>` и `git branch -D <branch-name>`
- [ ] **Проверить связанные issues**: Убедиться, что связанные задачи закрыты или корректно привязаны к PR
- [ ] **Проверить CI/CD на базовой ветке**: Убедиться, что все проверки и тесты прошли успешно на main/master после слияния
- [ ] **Отметить необходимость релиза/тега**: Если изменения требуют создания новой версии, создать тег или запланировать релиз

## Getting Help

If you're unsure about a PR:

1. **Ask for details**: Comment on the PR asking questions
2. **Request changes**: Use GitHub's "Request changes" review
3. **Get second opinion**: Tag another developer for review
4. **Test thoroughly**: Better safe than sorry

## Automation Setup (Recommended)

Add to `.github/workflows/pr-check.yml`:

```yaml
name: PR Checks
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pip install -r requirements.txt
          python -m pytest
      - name: Check for conflicts
        run: |
          git fetch origin main
          git merge-base --is-ancestor HEAD origin/main || echo "::warning::May have conflicts"
```

This will automatically check each PR for:
- Test failures
- Potential merge conflicts
- Code quality issues
