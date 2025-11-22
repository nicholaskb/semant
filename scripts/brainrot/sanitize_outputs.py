#!/usr/bin/env python3
"""
Sanitize AI-generated outputs to remove inner-monologue and thinking patterns.

This ensures investor-facing content is clean and professional.
"""
import re
from typing import Dict, Any, List, Optional


# Patterns that indicate AI inner-monologue or thinking
INNER_MONOLOGUE_PATTERNS = [
    r'\b(I am|I\'m|I\'m now|Let me|I will|I\'ll|I should|I need to|I want to|I think|I believe|I feel|I see|I notice|I observe|I understand|I realize|I recognize|I acknowledge|I consider|I evaluate|I analyze|I examine|I review|I assess|I determine|I conclude|I decide|I choose|I select|I pick|I opt|I go with|I went with|I\'m going with|I\'m choosing|I\'m selecting|I\'m picking|I\'m opting|I\'m deciding|I\'m concluding|I\'m determining|I\'m assessing|I\'m reviewing|I\'m examining|I\'m analyzing|I\'m evaluating|I\'m considering|I\'m acknowledging|I\'m recognizing|I\'m realizing|I\'m understanding|I\'m noticing|I\'m observing|I\'m seeing|I\'m feeling|I\'m believing|I\'m thinking)\b',
    r'\b(Now I|Now I\'m|Now let me|Now I will|Now I\'ll|Now I should|Now I need to|Now I want to|Now I think|Now I believe|Now I feel|Now I see|Now I notice|Now I observe|Now I understand|Now I realize|Now I recognize|Now I acknowledge|Now I consider|Now I evaluate|Now I analyze|Now I examine|Now I review|Now I assess|Now I determine|Now I conclude|Now I decide|Now I choose|Now I select|Now I pick|Now I opt)\b',
    r'\b(First,|Second,|Third,|Finally,|In conclusion,|To summarize,|In summary,|Let\'s|Let us|We should|We will|We\'ll|We need to|We want to|We think|We believe|We feel|We see|We notice|We observe|We understand|We realize|We recognize|We acknowledge|We consider|We evaluate|We analyze|We examine|We review|We assess|We determine|We conclude|We decide|We choose|We select|We pick|We opt)\b',
    r'\b(analyzing|reasoning|thinking|considering|evaluating|examining|reviewing|assessing|determining|concluding|deciding|choosing|selecting|picking|opting|acknowledging|recognizing|realizing|understanding|noticing|observing|seeing|feeling|believing)\b',
    r'\b(This is|This was|This would be|This could be|This might be|This should be|This will be|This can be|This has been|This had been|This will have been|This would have been|This could have been|This might have been|This should have been)\b',
    r'\b(Here\'s|Here is|Here are|Here we|Here I|Here\'s what|Here\'s how|Here\'s why|Here\'s where|Here\'s when|Here\'s who|Here\'s which|Here\'s that|Here\'s this)\b',
    r'\b(So,|So I|So we|So let|So now|So then|So here|So this|So that|So what|So how|So why|So where|So when|So who|So which)\b',
    r'\b(Well,|Well I|Well we|Well let|Well now|Well then|Well here|Well this|Well that|Well what|Well how|Well why|Well where|Well when|Well who|Well which)\b',
    r'\b(Actually,|Actually I|Actually we|Actually let|Actually now|Actually then|Actually here|Actually this|Actually that|Actually what|Actually how|Actually why|Actually where|Actually when|Actually who|Actually which)\b',
    r'\b(You know,|You see,|You understand,|You realize,|You notice,|You observe,|You feel,|You think,|You believe,|You know what,|You see what,|You understand what,|You realize what,|You notice what,|You observe what,|You feel what,|You think what,|You believe what)\b',
    r'\b(As you can see|As you might notice|As you probably know|As you may have noticed|As you likely know|As you might know|As you may know|As you can imagine|As you might imagine|As you probably imagine|As you may imagine|As you likely imagine|As you might imagine)\b',
    r'\b(It\'s important to note|It\'s worth noting|It\'s worth mentioning|It\'s worth pointing out|It\'s worth highlighting|It\'s worth emphasizing|It\'s worth stressing|It\'s worth underlining|It\'s worth noting that|It\'s worth mentioning that|It\'s worth pointing out that|It\'s worth highlighting that|It\'s worth emphasizing that|It\'s worth stressing that|It\'s worth underlining that)\b',
    r'\b(In my opinion|In my view|In my estimation|In my judgment|In my assessment|In my evaluation|In my analysis|In my examination|In my review|In my consideration|In my understanding|In my belief|In my thinking|In my feeling|In my observation|In my notice|In my recognition|In my realization|In my acknowledgment)\b',
    r'\b(I\'d like to|I would like to|I\'d want to|I would want to|I\'d prefer to|I would prefer to|I\'d rather|I would rather|I\'d suggest|I would suggest|I\'d recommend|I would recommend|I\'d advise|I would advise|I\'d propose|I would propose|I\'d offer|I would offer|I\'d put forward|I would put forward)\b',
    r'\b(To be honest|To be frank|To be fair|To be clear|To be precise|To be accurate|To be specific|To be exact|To be sure|To be certain|To be confident|To be positive|To be definite|To be absolute|To be complete|To be thorough|To be comprehensive|To be detailed|To be extensive|To be exhaustive)\b',
    r'\b(If I were you|If I were in your shoes|If I were in your position|If I were in your situation|If I were to|If I were going to|If I were to do|If I were to make|If I were to choose|If I were to select|If I were to pick|If I were to opt|If I were to decide|If I were to conclude|If I were to determine|If I were to assess|If I were to review|If I were to examine|If I were to analyze|If I were to evaluate|If I were to consider|If I were to acknowledge|If I were to recognize|If I were to realize|If I were to understand|If I were to notice|If I were to observe|If I were to see|If I were to feel|If I were to believe|If I were to think)\b',
    r'\b(One thing|One thing I|One thing we|One thing to|One thing that|One thing which|One thing this|One thing it|One thing you|One thing they|One thing he|One thing she|One thing is|One thing was|One thing will be|One thing would be|One thing could be|One thing might be|One thing should be|One thing can be|One thing has been|One thing had been|One thing will have been|One thing would have been|One thing could have been|One thing might have been|One thing should have been)\b',
    r'\b(Another thing|Another thing I|Another thing we|Another thing to|Another thing that|Another thing which|Another thing this|Another thing it|Another thing you|Another thing they|Another thing he|Another thing she|Another thing is|Another thing was|Another thing will be|Another thing would be|Another thing could be|Another thing might be|Another thing should be|Another thing can be|Another thing has been|Another thing had been|Another thing will have been|Another thing would have been|Another thing could have been|Another thing might have been|Another thing should have been)\b',
    r'\b(What I\'m|What I am|What we\'re|What we are|What I\'m doing|What I am doing|What we\'re doing|What we are doing|What I\'m going to do|What I am going to do|What we\'re going to do|What we are going to do|What I\'m trying to do|What I am trying to do|What we\'re trying to do|What we are trying to do|What I\'m attempting to do|What I am attempting to do|What we\'re attempting to do|What we are attempting to do)\b',
    r'\b(The reason|The reason I|The reason we|The reason to|The reason that|The reason which|The reason this|The reason it|The reason you|The reason they|The reason he|The reason she|The reason is|The reason was|The reason will be|The reason would be|The reason could be|The reason might be|The reason should be|The reason can be|The reason has been|The reason had been|The reason will have been|The reason would have been|The reason could have been|The reason might have been|The reason should have been)\b',
    r'\b(My reasoning|My thinking|My thought|My thoughts|My idea|My ideas|My opinion|My opinions|My view|My views|My perspective|My perspectives|My understanding|My understandings|My belief|My beliefs|My feeling|My feelings|My observation|My observations|My notice|My notices|My recognition|My recognitions|My realization|My realizations|My acknowledgment|My acknowledgments|My consideration|My considerations|My evaluation|My evaluations|My analysis|My analyses|My examination|My examinations|My review|My reviews|My assessment|My assessments|My determination|My determinations|My conclusion|My conclusions|My decision|My decisions|My choice|My choices|My selection|My selections|My pick|My picks|My opt|My opts)\b',
    r'\b(After careful|After careful I|After careful we|After careful to|After careful that|After careful which|After careful this|After careful it|After careful you|After careful they|After careful he|After careful she|After careful consideration|After careful evaluation|After careful analysis|After careful examination|After careful review|After careful assessment|After careful determination|After careful conclusion|After careful decision|After careful choice|After careful selection|After careful pick|After careful opt|After careful thinking|After careful thought|After careful thoughts|After careful idea|After careful ideas|After careful opinion|After careful opinions|After careful view|After careful views|After careful perspective|After careful perspectives|After careful understanding|After careful understandings|After careful belief|After careful beliefs|After careful feeling|After careful feelings|After careful observation|After careful observations|After careful notice|After careful notices|After careful recognition|After careful recognitions|After careful realization|After careful realizations|After careful acknowledgment|After careful acknowledgments)\b',
    r'\b(Upon reflection|Upon reflection I|Upon reflection we|Upon reflection to|Upon reflection that|Upon reflection which|Upon reflection this|Upon reflection it|Upon reflection you|Upon reflection they|Upon reflection he|Upon reflection she|Upon reflection,|Upon reflection:)\b',
    r'\b(It seems|It seems I|It seems we|It seems to|It seems that|It seems which|It seems this|It seems it|It seems you|It seems they|It seems he|It seems she|It seems like|It seems as if|It seems as though|It seems to be|It seems to have been|It seems to have|It seems to do|It seems to make|It seems to get|It seems to go|It seems to come|It seems to take|It seems to give|It seems to put|It seems to set|It seems to keep|It seems to let|It seems to see|It seems to know|It seems to think|It seems to feel|It seems to believe|It seems to understand|It seems to realize|It seems to recognize|It seems to acknowledge|It seems to consider|It seems to evaluate|It seems to analyze|It seems to examine|It seems to review|It seems to assess|It seems to determine|It seems to conclude|It seems to decide|It seems to choose|It seems to select|It seems to pick|It seems to opt)\b',
    r'\b(It appears|It appears I|It appears we|It appears to|It appears that|It appears which|It appears this|It appears it|It appears you|It appears they|It appears he|It appears she|It appears like|It appears as if|It appears as though|It appears to be|It appears to have been|It appears to have|It appears to do|It appears to make|It appears to get|It appears to go|It appears to come|It appears to take|It appears to give|It appears to put|It appears to set|It appears to keep|It appears to let|It appears to see|It appears to know|It appears to think|It appears to feel|It appears to believe|It appears to understand|It appears to realize|It appears to recognize|It appears to acknowledge|It appears to consider|It appears to evaluate|It appears to analyze|It appears to examine|It appears to review|It appears to assess|It appears to determine|It appears to conclude|It appears to decide|It appears to choose|It appears to select|It appears to pick|It appears to opt)\b',
    r'\b(It looks|It looks I|It looks we|It looks to|It looks that|It looks which|It looks this|It looks it|It looks you|It looks they|It looks he|It looks she|It looks like|It looks as if|It looks as though|It looks to be|It looks to have been|It looks to have|It looks to do|It looks to make|It looks to get|It looks to go|It looks to come|It looks to take|It looks to give|It looks to put|It looks to set|It looks to keep|It looks to let|It looks to see|It looks to know|It looks to think|It looks to feel|It looks to believe|It looks to understand|It looks to realize|It looks to recognize|It looks to acknowledge|It looks to consider|It looks to evaluate|It looks to analyze|It looks to examine|It looks to review|It looks to assess|It looks to determine|It looks to conclude|It looks to decide|It looks to choose|It looks to select|It looks to pick|It looks to opt)\b',
    r'\b(It might|It might I|It might we|It might to|It might that|It might which|It might this|It might it|It might you|It might they|It might he|It might she|It might be|It might have been|It might have|It might do|It might make|It might get|It might go|It might come|It might take|It might give|It might put|It might set|It might keep|It might let|It might see|It might know|It might think|It might feel|It might believe|It might understand|It might realize|It might recognize|It might acknowledge|It might consider|It might evaluate|It might analyze|It might examine|It might review|It might assess|It might determine|It might conclude|It might decide|It might choose|It might select|It might pick|It might opt)\b',
    r'\b(It could|It could I|It could we|It could to|It could that|It could which|It could this|It could it|It could you|It could they|It could he|It could she|It could be|It could have been|It could have|It could do|It could make|It could get|It could go|It could come|It could take|It could give|It could put|It could set|It could keep|It could let|It could see|It could know|It could think|It could feel|It could believe|It could understand|It could realize|It could recognize|It could acknowledge|It could consider|It could evaluate|It could analyze|It could examine|It could review|It could assess|It could determine|It could conclude|It could decide|It could choose|It could select|It could pick|It could opt)\b',
    r'\b(It should|It should I|It should we|It should to|It should that|It should which|It should this|It should it|It should you|It should they|It should he|It should she|It should be|It should have been|It should have|It should do|It should make|It should get|It should go|It should come|It should take|It should give|It should put|It should set|It should keep|It should let|It should see|It should know|It should think|It should feel|It should believe|It should understand|It should realize|It should recognize|It should acknowledge|It should consider|It should evaluate|It should analyze|It should examine|It should review|It should assess|It should determine|It should conclude|It should decide|It should choose|It should select|It should pick|It should opt)\b',
    r'\b(It would|It would I|It would we|It would to|It would that|It would which|It would this|It would it|It would you|It would they|It would he|It would she|It would be|It would have been|It would have|It would do|It would make|It would get|It would go|It would come|It would take|It would give|It would put|It would set|It would keep|It would let|It would see|It would know|It would think|It would feel|It would believe|It would understand|It would realize|It would recognize|It would acknowledge|It would consider|It would evaluate|It would analyze|It would examine|It would review|It would assess|It would determine|It would conclude|It would decide|It would choose|It would select|It would pick|It would opt)\b',
    r'\b(It will|It will I|It will we|It will to|It will that|It will which|It will this|It will it|It will you|It will they|It will he|It will she|It will be|It will have been|It will have|It will do|It will make|It will get|It will go|It will come|It will take|It will give|It will put|It will set|It will keep|It will let|It will see|It will know|It will think|It will feel|It will believe|It will understand|It will realize|It will recognize|It will acknowledge|It will consider|It will evaluate|It will analyze|It will examine|It will review|It will assess|It will determine|It will conclude|It will decide|It will choose|It will select|It will pick|It will opt)\b',
    r'\b(It can|It can I|It can we|It can to|It can that|It can which|It can this|It can it|It can you|It can they|It can he|It can she|It can be|It can have been|It can have|It can do|It can make|It can get|It can go|It can come|It can take|It can give|It can put|It can set|It can keep|It can let|It can see|It can know|It can think|It can feel|It can believe|It can understand|It can realize|It can recognize|It can acknowledge|It can consider|It can evaluate|It can analyze|It can examine|It can review|It can assess|It can determine|It can conclude|It can decide|It can choose|It can select|It can pick|It can opt)\b',
    r'\b(It may|It may I|It may we|It may to|It may that|It may which|It may this|It may it|It may you|It may they|It may he|It may she|It may be|It may have been|It may have|It may do|It may make|It may get|It may go|It may come|It may take|It may give|It may put|It may set|It may keep|It may let|It may see|It may know|It may think|It may feel|It may believe|It may understand|It may realize|It may recognize|It may acknowledge|It may consider|It may evaluate|It may analyze|It may examine|It may review|It may assess|It may determine|It may conclude|It may decide|It may choose|It may select|It may pick|It may opt)\b',
    r'\b(It must|It must I|It must we|It must to|It must that|It must which|It must this|It must it|It must you|It must they|It must he|It must she|It must be|It must have been|It must have|It must do|It must make|It must get|It must go|It must come|It must take|It must give|It must put|It must set|It must keep|It must let|It must see|It must know|It must think|It must feel|It must believe|It must understand|It must realize|It must recognize|It must acknowledge|It must consider|It must evaluate|It must analyze|It must examine|It must review|It must assess|It must determine|It must conclude|It must decide|It must choose|It must select|It must pick|It must opt)\b',
    r'\b(It might be|It could be|It should be|It would be|It will be|It can be|It may be|It must be|It has to be|It has got to be|It\'s got to be|It\'s to be|It is to be|It was to be|It will have to be|It would have to be|It could have to be|It might have to be|It should have to be|It may have to be|It can have to be|It must have to be)\b',
    r'\b(It seems to me|It appears to me|It looks to me|It might be to me|It could be to me|It should be to me|It would be to me|It will be to me|It can be to me|It may be to me|It must be to me|It has to be to me|It has got to be to me|It\'s got to be to me|It\'s to be to me|It is to be to me|It was to be to me|It will have to be to me|It would have to be to me|It could have to be to me|It might have to be to me|It should have to be to me|It may have to be to me|It can have to be to me|It must have to be to me)\b',
    r'\b(It seems like|It appears like|It looks like|It might be like|It could be like|It should be like|It would be like|It will be like|It can be like|It may be like|It must be like|It has to be like|It has got to be like|It\'s got to be like|It\'s to be like|It is to be like|It was to be like|It will have to be like|It would have to be like|It could have to be like|It might have to be like|It should have to be like|It may have to be like|It can have to be like|It must have to be like)\b',
    r'\b(It seems as if|It appears as if|It looks as if|It might be as if|It could be as if|It should be as if|It would be as if|It will be as if|It can be as if|It may be as if|It must be as if|It has to be as if|It has got to be as if|It\'s got to be as if|It\'s to be as if|It is to be as if|It was to be as if|It will have to be as if|It would have to be as if|It could have to be as if|It might have to be as if|It should have to be as if|It may have to be as if|It can have to be as if|It must have to be as if)\b',
    r'\b(It seems as though|It appears as though|It looks as though|It might be as though|It could be as though|It should be as though|It would be as though|It will be as though|It can be as though|It may be as though|It must be as though|It has to be as though|It has got to be as though|It\'s got to be as though|It\'s to be as though|It is to be as though|It was to be as though|It will have to be as though|It would have to be as though|It could have to be as though|It might have to be as though|It should have to be as though|It may have to be as though|It can have to be as though|It must have to be as though)\b',
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in INNER_MONOLOGUE_PATTERNS]


def sanitize_text(text: str) -> str:
    """
    Remove AI inner-monologue patterns from text.
    
    Args:
        text: Input text that may contain AI thinking patterns
        
    Returns:
        Sanitized text with inner-monologue removed
    """
    if not text or not isinstance(text, str):
        return text if text else ""
    
    # Remove patterns
    sanitized = text
    for pattern in COMPILED_PATTERNS:
        sanitized = pattern.sub('', sanitized)
    
    # Clean up extra whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip()
    
    # Remove leading/trailing punctuation that might be left over
    sanitized = re.sub(r'^[,\s\.;:!?\-]+|[,\s\.;:!?\-]+$', '', sanitized)
    
    return sanitized


def sanitize_explanation(explanation: str) -> str:
    """
    Sanitize explanation field specifically.
    
    Args:
        explanation: Explanation text from AI
        
    Returns:
        Clean explanation without inner-monologue
    """
    if not explanation:
        return ""
    
    sanitized = sanitize_text(explanation)
    
    # If sanitization removed everything, provide a fallback
    if not sanitized or len(sanitized.strip()) < 3:
        return "Viral content combination"
    
    return sanitized


def sanitize_combination(combo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a combination dictionary, removing AI inner-monologue from all text fields.
    
    Args:
        combo: Combination dictionary
        
    Returns:
        Sanitized combination dictionary
    """
    if not isinstance(combo, dict):
        return combo
    
    sanitized = combo.copy()
    
    # Sanitize explanation field
    if "explanation" in sanitized:
        sanitized["explanation"] = sanitize_explanation(sanitized.get("explanation", ""))
    
    # Sanitize combined_prompt if it exists
    if "combined_prompt" in sanitized and isinstance(sanitized["combined_prompt"], str):
        sanitized["combined_prompt"] = sanitize_text(sanitized["combined_prompt"])
    
    # Sanitize any other string fields that might contain AI output
    for key, value in sanitized.items():
        if isinstance(value, str) and key not in ["american_objects", "italian_phrases"]:
            sanitized[key] = sanitize_text(value)
    
    return sanitized


def sanitize_combinations(combinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize a list of combinations.
    
    Args:
        combinations: List of combination dictionaries
        
    Returns:
        List of sanitized combinations
    """
    if not isinstance(combinations, list):
        return combinations
    
    return [sanitize_combination(combo) for combo in combinations]


def sanitize_ai_response(content: str) -> str:
    """
    Sanitize raw AI response content before parsing.
    
    Args:
        content: Raw AI response text
        
    Returns:
        Sanitized content
    """
    if not content:
        return content
    
    # Remove common AI thinking prefixes
    lines = content.split('\n')
    sanitized_lines = []
    
    for line in lines:
        # Skip lines that are clearly AI thinking
        if any(pattern.search(line) for pattern in COMPILED_PATTERNS[:10]):
            continue
        sanitized_lines.append(line)
    
    return '\n'.join(sanitized_lines)
