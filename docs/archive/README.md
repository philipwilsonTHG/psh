# Archive Directory

This directory contains superseded planning and design documents that have been consolidated into newer, more comprehensive documentation.

## Archived Executor Improvement Documents

The following executor-related recommendations documents have been **superseded** by:
**`/docs/executor_improvements.md`** (Consolidated master document)

### Archived Files:

1. **`EXECUTOR_IMPROVEMENT_RECOMMENDATIONS.md`** (2025-11-18)
   - Original 3 recommendations focusing on:
     - Unifying process creation logic
     - SIGCHLD handler safety (self-pipe trick)
     - Process group setup race condition

2. **`EXECUTOR_SIGNAL_AND_JOB_CONTROL_NOTES.md`** (2025-11-18)
   - 5 incremental improvement recommendations:
     - Centralize signal reset logic
     - Process group synchronization improvements
     - Surface tcsetpgrp failures
     - Unify foreground cleanup
     - SIGCHLD strategy considerations

3. **`executor_improvement_recommendations.md`** (2025-01-18)
   - Comprehensive 10-recommendation document with:
     - Complete implementation code
     - High/Medium/Low priority classification
     - Testing strategies
     - Metrics and observability focus

## Consolidated Document

All recommendations from the above documents have been merged into:

**`/docs/executor_improvements.md`**

This consolidated document provides:
- ✅ Single source of truth for all executor improvements
- ✅ Clear priority classification (Critical/High/Medium/Low)
- ✅ Complete, production-ready implementations
- ✅ 4-phase implementation roadmap
- ✅ Comprehensive testing strategy
- ✅ Status tracking appendix

## Other Archived Documents

This archive also contains historical planning documents for various PSH features that have been implemented or superseded. These are kept for historical reference but should not be used as current guidance.

---

**Note**: When referencing executor improvements, always use the consolidated document at `/docs/executor_improvements.md`.
