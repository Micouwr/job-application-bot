# The Golden Rules

> Strict quality standards for production-ready code

## Rule #1: Never Assume + Document Factually
Verify every assumption before building on it. All documentation must reflect actual code state, not aspirational features. Example: README.md must match gui/tkinter_app.py functionality exactly. No documenting unimplemented features.

- Check if files exist before reading
- Confirm method signatures before calling
- Validate user input before processing
- Test API responses before parsing
- Ensure README.md matches actual GUI workflow

Example: Before inserting analyze_match, verify line 427 is correct insertion point.

## Rule #2: Verify Before AND After Fixing
Confirm the problem exists before applying solutions. Verify code BEFORE providing it (check for issues) AND AFTER providing it (confirm it works). Must review what was provided to ensure no coding issues.

- Reproduce the bug before fixing
- Check method counts before AND after declaring success
- Validate ASCII values before AND after committing
- Import modules after changes to ensure compatibility
- Review provided code for nested quote issues, ASCII violations

Example: Run grep before AND after method insertion to verify no duplication.

## Rule #3: Complete Files Only
No partial code; always provide full context.

- Atomic file operations only
- No partial method replacements
- Full context for debugging
- Single-command operations when possible

Example: Replace entire start_tailoring method, not just the validation section.

## Rule #4: SAVE POINTS ARE MANDATORY
Document every major state change with full context. Before rebuild, state: "Do not proceed until..." User has final authority on all architectural decisions.

SAVE POINT Documentation Requirements:
1. State Change Context: What is being changed and why
2. Before State: "Do not proceed until..." explicit checkpoint
3. User Authority: Final approval required before proceeding
4. Full Context: Code state, environment, decisions made
5. Failure Documentation: What failed, why, how fixed, what learned

Example: SAVE POINT #155 documentation included: initial failures (3 reconstruction attempts), root cause (regex assumptions), fix (direct write method), learned (verify before & after).

## Rule #5: No Band-Aids
Fix problems correctly, don't apply temporary patches.

- Use minimal token scopes, not admin everything
- Create properly-scoped tokens instead of reusing expired ones
- Use atomic reconstruction instead of sed/regex hacks
- Solve environment issues, don't work around them

## Rule #6: ASCII Only (0-127)
No Unicode characters in codebase.

- Max ASCII value must be less than or equal to 127
- Verify before every commit
- No emojis in code files
- No special characters in strings

Example: README.md ASCII: 125, Code ASCII: 126 (both verified)

---

## Compliance Verification (v2.1.0)

```bash
# Rule #2 & #6: Import and ASCII check
python3 -c "import gui.tkinter_app; print('Import: PASS')" 2>&1
python3 -c "print(f'Max ASCII: {max(ord(c) for c in open(\"gui/tkinter_app.py\").read())}')"

# Rule #2: Method count verification (Before & After)
grep -c "def analyze_match" gui/tkinter_app.py  # Should be 1

# Rule #5: Security audit
grep -c "filedialog.askopenfilename" gui/tkinter_app.py  # Should be 1 (only in upload_resume)
