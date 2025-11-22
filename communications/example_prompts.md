# Example Prompts for Agent Diary System

## Strategy Lead Prompts

### Weekly Strategy Review
```
As Strategy Lead, please:
1. Review all client interactions from the past week
2. Document key strategic decisions made
3. Note any risks or opportunities identified
4. Plan next week's strategic priorities
5. Log all of this in your diary with appropriate context
```

### Client Meeting Preparation
```
Before the upcoming client meeting:
1. Review all previous client interactions
2. Analyze current strategy alignment
3. Prepare key talking points
4. Document your preparation process in your diary
5. Note any areas requiring team input
```

## Engagement Manager Prompts

### Project Status Review
```
As Engagement Manager:
1. Review all team member diaries from the past week
2. Identify any blockers or risks
3. Document project timeline status
4. Note any client concerns
5. Log a comprehensive status update in your diary
```

### Team Performance Assessment
```
Please:
1. Review all team member diaries for the past month
2. Identify patterns in team performance
3. Note any areas needing attention
4. Document successful strategies
5. Log your assessment in your diary
```

## Implementation Lead Prompts

### Technical Review
```
As Implementation Lead:
1. Review all technical decisions made this week
2. Document any technical debt identified
3. Note implementation challenges
4. Plan technical improvements
5. Log your technical review in your diary
```

### Process Optimization
```
Please:
1. Review current implementation processes
2. Identify bottlenecks
3. Document optimization opportunities
4. Note team feedback
5. Log your process analysis in your diary
```

## Value Realization Lead Prompts

### ROI Analysis
```
As Value Realization Lead:
1. Review all value metrics for the past quarter
2. Document ROI calculations
3. Note any deviations from targets
4. Identify improvement opportunities
5. Log your analysis in your diary
```

### Client Value Assessment
```
Please:
1. Review all client value metrics
2. Document value delivery status
3. Note any value gaps
4. Identify value optimization opportunities
5. Log your assessment in your diary
```

## Cross-Team Collaboration Prompts

### Team Sync
```
All team leads:
1. Review each other's diaries for the past week
2. Document any cross-team dependencies
3. Note collaboration opportunities
4. Identify potential conflicts
5. Log your team sync findings in your diaries
```

### Client Value Review
```
All team leads:
1. Review client value metrics
2. Document your team's contribution
3. Note any cross-team value opportunities
4. Identify value delivery challenges
5. Log your value review in your diaries
```

## How to Use These Prompts

1. Copy the prompt you want to try
2. Send it to the appropriate agent(s)
3. The agent will:
   - Process the request
   - Document their actions in their diary
   - Add entries to the knowledge graph
4. You can then query the knowledge graph to see:
   - How the agent responded
   - What they documented
   - How it relates to other entries

## Example SPARQL Queries

### Find All Diary Entries for a Specific Prompt
```sparql
SELECT ?agent ?entry ?message ?timestamp
WHERE {
    ?agent dm:hasDiaryEntry ?entry .
    ?entry dm:message ?message ;
           dm:timestamp ?timestamp .
    FILTER(CONTAINS(?message, "weekly strategy review"))
}
```

### Find Cross-Team Collaboration Entries
```sparql
SELECT ?agent ?entry ?message
WHERE {
    ?agent dm:hasDiaryEntry ?entry .
    ?entry dm:message ?message .
    FILTER(CONTAINS(?message, "team sync") || 
           CONTAINS(?message, "cross-team"))
}
```

### Find Value-Related Entries
```sparql
SELECT ?agent ?entry ?message
WHERE {
    ?agent dm:hasDiaryEntry ?entry .
    ?entry dm:message ?message .
    FILTER(CONTAINS(?message, "value") || 
           CONTAINS(?message, "ROI") ||
           CONTAINS(?message, "metrics"))
}
``` 