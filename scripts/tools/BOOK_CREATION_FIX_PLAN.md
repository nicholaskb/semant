# Book Creation Workflow - Fix Plan

## Overview
This plan addresses the critical issues preventing the book creation workflow from completing successfully.

## Issues Identified

### Critical (P0)
1. **URI Encoding Bug in ResearchAgent** - Workflow stops at research phase
   - ResearchAgent creates invalid URIs with apostrophes/spaces
   - KG serialization fails
   - Blocks entire workflow

### High Priority (P1)
2. **Missing Error Handling** - No fallback when research fails
   - Should fallback to STORY_SCRIPT if research fails
   - Should continue workflow even if research has issues

3. **Email Filtering Too Aggressive** - Replying to newsletters
   - Currently replies to all emails containing "mckinsey"
   - Should only reply to actual email replies or known contacts

### Medium Priority (P2)
4. **Monitoring & Reporting** - Need better progress tracking
   - Monitor script created but needs integration
   - Need real-time progress reporting

5. **Testing** - Full end-to-end test needed
   - Test complete workflow after fixes
   - Verify all phases complete successfully

## Implementation Plan

### Task 1: Fix URI Encoding in ResearchAgent
**Priority:** P0 (Critical)
**Estimated Time:** 30 minutes

**Steps:**
1. Update `agents/core/research_agent.py` to properly encode URIs
2. Use URL encoding or hash-based URIs for topics
3. Test with topics containing special characters

**Acceptance Criteria:**
- ResearchAgent can handle topics with apostrophes, spaces, special chars
- KG serialization succeeds
- Research phase completes without errors

### Task 2: Add Error Handling for Research Failures
**Priority:** P1 (High)
**Estimated Time:** 20 minutes

**Steps:**
1. Wrap research call in try/except
2. Fallback to empty findings if research fails
3. Continue workflow with STORY_SCRIPT if needed
4. Log warnings but don't stop workflow

**Acceptance Criteria:**
- Workflow continues even if research fails
- Falls back to STORY_SCRIPT gracefully
- Error logged but doesn't crash

### Task 3: Improve Email Filtering
**Priority:** P1 (High)
**Estimated Time:** 30 minutes

**Steps:**
1. Check for `in_reply_to` or `references` headers
2. Maintain list of known contacts
3. Skip marketing/newsletter emails
4. Only process actual replies or known contacts

**Acceptance Criteria:**
- Only replies to actual email replies
- Skips newsletters and marketing emails
- Known contacts list configurable

### Task 4: Add Progress Monitoring Integration
**Priority:** P2 (Medium)
**Estimated Time:** 45 minutes

**Steps:**
1. Integrate monitor script into main workflow
2. Add progress callbacks at each phase
3. Generate progress reports
4. Save monitoring data to KG

**Acceptance Criteria:**
- Real-time progress visible during execution
- Progress reports generated
- Monitoring data stored in KG

### Task 5: End-to-End Testing
**Priority:** P2 (Medium)
**Estimated Time:** 60 minutes

**Steps:**
1. Run complete workflow with fixes
2. Verify all phases complete
3. Check KG for all expected data
4. Verify HTML output generated
5. Test resume functionality

**Acceptance Criteria:**
- All phases complete successfully
- KG contains all expected data
- HTML file generated with images
- Can resume workflow from any point

## Dependencies

- Task 1 must complete before Task 2
- Tasks 1-3 should complete before Task 5
- Task 4 can be done in parallel

## Success Metrics

- ✅ Research phase completes without URI errors
- ✅ Workflow completes all phases
- ✅ Images generated and selected
- ✅ McKinsey reviews completed
- ✅ HTML output generated
- ✅ Email filtering works correctly
- ✅ Workflow can be resumed

