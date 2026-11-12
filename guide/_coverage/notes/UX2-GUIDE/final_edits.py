from helpers import update
update('guide/model/define-a-consumer-api.md',[
('''   no value. Save the value or cancel. Use the served type: a text fallback cannot stand''','''   no value. Leave the input or press Enter to save; Escape puts the old value back.
   An unchanged input saves nothing. If refused, review the reason beneath it and use
   **Save again** to retry or **Cancel** to abandon the edit. Use the served type: a text fallback cannot stand''')],
'Corrected Default cell saving and refusal recovery; retained the multi-field consumer forms.')
update('use/records.md',[
('''A saved value shows **‹Field› saved** with **Undo**, including a value set for the first time:''','''Saving through an input shows **‹Field› saved** with **Undo**, including a value set for the first time:'''),
('''**Cleared** and **Empty text** still appear when already stored, but cannot be set through
these in-place inputs.''','''**Cleared** and **Empty text** still appear when already stored. There is no **No value**
choice in the input: emptying a text input removes its value rather than setting either state.''')],
'Clarified that input notices differ from the unchanged direct Yes/No controls, and described empty text inputs precisely.',
'The structured-value input still parses literal null; the changelog’s blanket statement about Cleared needs clarification.')
