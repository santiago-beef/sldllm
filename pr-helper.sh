#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# pr-helper.sh — Interactive guide to the 7-step PR ritual
#
# Usage:  ./pr-helper.sh
#
# Walks you through creating a branch, making a change, committing
# with proper attribution, pushing, and opening a pull request.
# Explains every term and command before running it.
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colors & formatting ──────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
RESET='\033[0m'

banner()  { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════${RESET}"; }
step()    { echo -e "\n${BOLD}${GREEN}▶ STEP $1${RESET}${BOLD} — $2${RESET}"; }
info()    { echo -e "  ${CYAN}ℹ${RESET}  $1"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
err()     { echo -e "  ${RED}✖${RESET}  $1"; }
ok()      { echo -e "  ${GREEN}✔${RESET}  $1"; }
dimcmd()  { echo -e "  ${DIM}\$ $1${RESET}"; }
explain() { echo -e "\n  ${BOLD}What does that mean?${RESET}"; echo -e "  $1\n"; }

pause() {
    echo ""
    read -rp "  Press ENTER to continue (or type 'quit' to exit)... " ans
    if [[ "${ans,,}" == "quit" ]]; then
        echo -e "\n${YELLOW}No worries — pick up where you left off anytime!${RESET}\n"
        exit 0
    fi
}

run_and_show() {
    dimcmd "$1"
    echo ""
    eval "$1" 2>&1 | sed 's/^/    /'
    echo ""
}

ask() {
    local prompt="$1" var="$2"
    read -rp "  $prompt " "$var"
}

# ── Pre-flight check ─────────────────────────────────────────────
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    err "This doesn't look like a git repo. Run this script from inside your repo folder."
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

# ── Welcome ──────────────────────────────────────────────────────
clear
banner
echo -e "${BOLD}  🚀 PR Helper — The 7-Step Pull Request Ritual${RESET}"
banner

echo ""
echo -e "  This script walks you through making a change the"
echo -e "  ${BOLD}open-source way${RESET}: branch → edit → commit → push → PR."
echo ""
echo -e "  ${BOLD}Quick glossary before we start:${RESET}"
echo ""
echo -e "  ${CYAN}repo${RESET}      = your project folder, tracked by git"
echo -e "  ${CYAN}commit${RESET}    = a saved snapshot of your files, with a message"
echo -e "  ${CYAN}branch${RESET}    = a separate line of work (so you don't break main)"
echo -e "  ${CYAN}main${RESET}      = the shared branch everyone sees — never edit directly"
echo -e "  ${CYAN}PR${RESET}        = Pull Request — asking to merge your branch into main"
echo -e "  ${CYAN}staging${RESET}   = choosing which files go into your next commit"
echo -e "  ${CYAN}push${RESET}      = uploading your commits to GitHub"
echo -e "  ${CYAN}trailer${RESET}   = a line at the end of a commit naming your AI co-author"

echo ""
echo -e "  You are in repo: ${BOLD}$REPO_NAME${RESET}"
echo -e "  Repo location:   ${DIM}$REPO_ROOT${RESET}"

pause

# ══════════════════════════════════════════════════════════════════
# STEP 1 — Start from fresh main
# ══════════════════════════════════════════════════════════════════
step 1 "Start from fresh main"

info "Before any new work, we make sure our 'main' branch has the"
info "latest stuff from GitHub. Think of it as refreshing the page."

echo ""
info "Running two commands:"
info "  ${BOLD}git switch main${RESET} — go to the main branch"
info "  ${BOLD}git pull${RESET}         — download any new changes from GitHub"

pause

run_and_show "git switch main"
run_and_show "git pull"

CURRENT=$(git branch --show-current)
if [[ "$CURRENT" == "main" ]]; then
    ok "You're on 'main' and up to date!"
else
    warn "Something unexpected — you're on branch '$CURRENT' instead of main."
    warn "Try running: git switch main"
fi

explain "You always start here so your new work is based on the latest version."

pause

# ══════════════════════════════════════════════════════════════════
# STEP 2 — Create a branch
# ══════════════════════════════════════════════════════════════════
step 2 "Create a branch for your change"

info "A ${BOLD}branch${RESET} is like a copy of main where you can safely make changes"
info "without affecting anyone else. Name it after what you're doing."
echo ""
info "Examples of good branch names:"
info "  add-my-project-card"
info "  fix-readme-typo"
info "  update-project-status"
echo ""

ask "What should we name your branch? (lowercase-with-hyphens):" BRANCH_NAME

# Sanitize the branch name
BRANCH_NAME=$(echo "$BRANCH_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')

if [[ -z "$BRANCH_NAME" ]]; then
    BRANCH_NAME="my-new-change"
    warn "No name given — using '${BRANCH_NAME}'"
fi

info "Creating and switching to branch: ${BOLD}$BRANCH_NAME${RESET}"
info "Command: ${BOLD}git switch -c $BRANCH_NAME${RESET}"
info "  -c means 'create' — without it, git looks for an existing branch."

pause

run_and_show "git switch -c $BRANCH_NAME"

CURRENT=$(git branch --show-current)
if [[ "$CURRENT" == "$BRANCH_NAME" ]]; then
    ok "You're now on branch '$BRANCH_NAME' — main is safe!"
else
    err "Something went wrong. You're on '$CURRENT'."
fi

explain "Everything you do now happens on this branch only. Main stays untouched."

pause

# ══════════════════════════════════════════════════════════════════
# STEP 3 — Make your change
# ══════════════════════════════════════════════════════════════════
step 3 "Make your change"

info "Now you edit files — with any editor, or your AI assistant."
info "The key rule: ${BOLD}one PR does one thing${RESET}."
info "  ✅ Add your project card"
info "  ✅ Fix a typo"
info "  ❌ Do five unrelated things at once"
echo ""
info "Go ahead and make your edits now."
info "(If you haven't made changes yet, do so before continuing.)"
echo ""

pause

info "Let's see what changed:"
run_and_show "git status"

explain "'git status' shows which files you added, modified, or deleted.\n  ${RED}Red${RESET} files = changed but not staged yet.\n  ${GREEN}Green${RESET} files = staged and ready to commit."

pause

# ══════════════════════════════════════════════════════════════════
# STEP 4 — Inspect and stage
# ══════════════════════════════════════════════════════════════════
step 4 "Inspect your changes, then stage them"

info "${BOLD}Staging${RESET} = telling git which changed files should go in the next commit."
info "Think of it as putting items in a box before sealing (committing) it."
echo ""
info "Let's look at what changed line-by-line:"
run_and_show "git diff"

echo ""
info "Now we ${BOLD}stage${RESET} (add) the files."
echo ""
echo -e "  ${BOLD}Options:${RESET}"
echo -e "    1) Stage ALL changes (git add .)"
echo -e "    2) Stage specific file(s)"
echo ""
ask "Pick 1 or 2:" STAGE_CHOICE

case "$STAGE_CHOICE" in
    1)
        info "Staging everything..."
        run_and_show "git add ."
        ;;
    2)
        ask "Enter file path(s) separated by spaces:" FILES
        if [[ -n "$FILES" ]]; then
            run_and_show "git add $FILES"
        else
            warn "No files entered — staging everything instead."
            run_and_show "git add ."
        fi
        ;;
    *)
        info "Staging everything..."
        run_and_show "git add ."
        ;;
esac

info "Let's verify what's staged:"
run_and_show "git status"

ok "Green files are staged and ready to be committed!"

explain "Staging lets you control exactly what goes into each commit.\n  Changed your mind? Run: git restore --staged <file>"

pause

# ══════════════════════════════════════════════════════════════════
# STEP 5 — Commit with message + co-author trailer
# ══════════════════════════════════════════════════════════════════
step 5 "Commit with a message and your AI co-author"

info "A ${BOLD}commit${RESET} saves a snapshot of your staged files with a message."
info "In this course, every commit where an AI helped ${BOLD}must${RESET} include a"
info "'Co-Authored-By' ${BOLD}trailer${RESET} — a line naming the exact model."
echo ""
info "Example trailers:"
echo -e "    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
echo -e "    Co-Authored-By: GPT-5.2 <noreply@openai.com>"
echo -e "    Co-Authored-By: Gemini 3 Pro <noreply@google.com>"
echo -e "    Co-Authored-By: Qwen3-Coder (self-hosted) <noreply@localhost>"
echo ""

ask "Commit message (what did you do?):" COMMIT_MSG

if [[ -z "$COMMIT_MSG" ]]; then
    COMMIT_MSG="Update files"
    warn "No message given — using '$COMMIT_MSG'"
fi

echo ""
info "Did an AI model help with this change?"
ask "Enter the model name (or press ENTER if you did it all by hand):" MODEL_NAME

if [[ -n "$MODEL_NAME" ]]; then
    ask "Model's email domain (e.g. anthropic.com, openai.com, google.com, localhost):" MODEL_DOMAIN
    if [[ -z "$MODEL_DOMAIN" ]]; then
        MODEL_DOMAIN="localhost"
    fi
    TRAILER="Co-Authored-By: $MODEL_NAME <noreply@$MODEL_DOMAIN>"
    info "Your commit will include:"
    echo -e "    ${BOLD}$COMMIT_MSG${RESET}"
    echo -e "    ${DIM}$TRAILER${RESET}"
    pause
    run_and_show "git commit -m \"$COMMIT_MSG\" -m \"$TRAILER\""
else
    info "No AI co-author — committing as solo work."
    pause
    run_and_show "git commit -m \"$COMMIT_MSG\""
fi

info "Let's verify the commit:"
run_and_show "git log --oneline -1"

ok "Your change is saved locally!"

explain "The commit only exists on YOUR machine right now.\n  Next we push it to GitHub so others can see it."

pause

# ══════════════════════════════════════════════════════════════════
# STEP 6 — Push and open a PR
# ══════════════════════════════════════════════════════════════════
step 6 "Push to GitHub and open a Pull Request"

info "${BOLD}Pushing${RESET} uploads your branch and commits to GitHub."
info "Command: ${BOLD}git push -u origin $BRANCH_NAME${RESET}"
info "  -u = 'set upstream' (only needed the first time)"
info "  origin = GitHub (where your repo lives online)"
echo ""

pause

run_and_show "git push -u origin $BRANCH_NAME"

ok "Your branch is now on GitHub!"

# Try to build the PR URL
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$REMOTE_URL" == *github.com* ]]; then
    # Extract owner/repo from HTTPS or SSH URL
    PR_PATH=$(echo "$REMOTE_URL" | sed -E 's#(https://github.com/|git@github.com:)##; s/\.git$//')
    PR_URL="https://github.com/$PR_PATH/compare/main...$BRANCH_NAME?expand=1"
    echo ""
    info "${BOLD}Open this link to create your PR:${RESET}"
    echo -e "\n    ${CYAN}${BOLD}$PR_URL${RESET}\n"
fi

echo ""
info "When you open the PR page, fill out the template:"
echo ""
echo -e "    ${BOLD}What this PR does${RESET} (1–2 sentences):"
echo -e "    ${BOLD}How I verified it${RESET} (what did you check?):"
echo -e "    ☐ One change, one PR"
echo -e "    ☐ Commits carry Co-Authored-By trailer"
echo -e "    ☐ No personal data (usernames only)"

explain "A ${BOLD}Pull Request${RESET} (PR) is how you propose your change.\n  Other people can review the differences, leave comments,\n  and approve before it gets merged into main."

pause

# ══════════════════════════════════════════════════════════════════
# STEP 7 — After review: merge and clean up
# ══════════════════════════════════════════════════════════════════
step 7 "After review — merge and clean up"

info "This step happens ${BOLD}after${RESET} your PR is reviewed and approved on GitHub."
echo ""
info "If reviewers request changes:"
echo -e "    1. Make the edits on this same branch"
echo -e "    2. git add → git commit → git push  (the PR updates itself)"
echo ""
info "Once approved, click ${BOLD}Merge${RESET} on GitHub, then ${BOLD}Delete branch${RESET}."
echo ""
info "Then clean up locally:"
echo -e "    ${DIM}\$ git switch main${RESET}"
echo -e "    ${DIM}\$ git pull${RESET}"
echo -e "    ${DIM}\$ git branch -d $BRANCH_NAME${RESET}"
echo ""

ask "Has your PR been merged? (yes/no):" MERGED

if [[ "${MERGED,,}" == "yes" || "${MERGED,,}" == "y" ]]; then
    info "Cleaning up..."
    run_and_show "git switch main"
    run_and_show "git pull"
    git branch -d "$BRANCH_NAME" 2>/dev/null && ok "Branch '$BRANCH_NAME' deleted locally." || warn "Branch may already be gone — that's fine."
    echo ""
    ok "All clean! You're back on main with the latest code."
else
    info "No worries! Come back and run these commands after it's merged:"
    echo -e "    ${DIM}\$ git switch main${RESET}"
    echo -e "    ${DIM}\$ git pull${RESET}"
    echo -e "    ${DIM}\$ git branch -d $BRANCH_NAME${RESET}"
fi

# ── Done! ─────────────────────────────────────────────────────────
banner
echo -e "${BOLD}  🎉 You did it! Here's what happened:${RESET}"
banner

echo ""
echo -e "  ${GREEN}Step 1${RESET}  Started from fresh main           ${DIM}(git switch main + git pull)${RESET}"
echo -e "  ${GREEN}Step 2${RESET}  Created branch '$BRANCH_NAME'     ${DIM}(git switch -c ...)${RESET}"
echo -e "  ${GREEN}Step 3${RESET}  Made your change                   ${DIM}(edited files)${RESET}"
echo -e "  ${GREEN}Step 4${RESET}  Inspected and staged               ${DIM}(git diff + git add)${RESET}"
echo -e "  ${GREEN}Step 5${RESET}  Committed with co-author trailer   ${DIM}(git commit -m ... -m ...)${RESET}"
echo -e "  ${GREEN}Step 6${RESET}  Pushed and opened a PR             ${DIM}(git push -u origin ...)${RESET}"
echo -e "  ${GREEN}Step 7${RESET}  Review → merge → clean up          ${DIM}(merge on GitHub + branch -d)${RESET}"
echo ""
echo -e "  Run ${BOLD}./pr-helper.sh${RESET} again anytime you need to make a new change!"
echo ""
