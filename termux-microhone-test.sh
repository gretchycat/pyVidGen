#!/bin/bash
clear
echo -e "\x1b[0;1;94mThe purpose of this script is to find your android mic sweet spot."
echo "  Read the prompt and press enter when done:"
read
for i in 8000 10025 12000 16000 22050 24000 32000 44100 48000; do
    echo -e "\x1b[0mprompt: \x1b[0;1;97mTesting 1, 2, 3. Recording at $i Hz\x1b[0m"
    termux-microphone-record -r $i -f test-$i.mp3
    read
    termux-microphone-record -q
done


