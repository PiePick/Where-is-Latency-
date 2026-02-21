# Reaction Analysis v01

## Strategy Count
- echo_first: 2
- emotion_first: 4
- bridge: 4

## Emotion Count
- positive: 4
- negative: 3
- ambiguous: 3

## Per-turn Table

| text | emotion | strategy | reaction | top1 | margin | entropy |
|---|---|---|---|---:|---:|---:|
| I passed the exam and I feel amazing. | positive | echo_first | Right, on that— | 0.8 | 0.6412 | 0.4525 |
| I am scared about tomorrow's interview. | negative | emotion_first | I hear you. | 0.8996 | 0.8479 | 0.2931 |
| I am just drinking water now. | positive | bridge | Right— | 0.5809 | 0.3486 | 0.7622 |
| My friend ignored my message and I feel sad. | negative | emotion_first | That’s great. | 0.9113 | 0.8638 | 0.2695 |
| Wow, I didn't expect this at all. | ambiguous | bridge | I’m here— | 0.7211 | 0.5695 | 0.5911 |
| Can you explain this one more time? | ambiguous | emotion_first | That sounds rough. | 0.5529 | 0.2421 | 0.7208 |
| Everything is fine, just a normal day. | positive | emotion_first | That’s great. | 0.7113 | 0.5875 | 0.6463 |
| I am angry because my work got rejected. | negative | bridge | Mm, go on— | 0.9237 | 0.8839 | 0.2388 |
| I feel curious about this project idea. | ambiguous | bridge | I’m here— | 0.6806 | 0.4186 | 0.5759 |
| I am relieved that the surgery ended well. | positive | echo_first | Okay, about that— | 0.8156 | 0.7014 | 0.4574 |
