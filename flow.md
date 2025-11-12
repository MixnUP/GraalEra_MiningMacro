1st phase : Search Flow Algorithm:
    - Search for rocks in the detection region
    - If rock is found, switch to 2nd phase
    - If no rock is found, perform mining action (Click) once
    - Search for rocks in the detection region, if still no rock is found, move to next detection region
    - repeat 1st phase
2nd phase : Mining Flow Algorithm:
    - Check for minable rocks (If no rock is found, go back to 1st phase)
    - Perform mining action (Click)
    - If rock_phase_4 or rock_phase_4_2 is found, switch to next detection region {breaks loop}
    - else, repeat 2nd phase every 2 seconds