# Ableton Live / Komplete Kontrol integration

This is a replacement for the Host Integration scripts for using the Komplete Kontrol S-series keyboards with Ableton Live 9.2+.

**Do I need this?** Yes, if you want to control Ableton track volume faders and device macro controls from your controller.

![keyboards](https://raw.githubusercontent.com/bosgood/ableton_komplete_kontrol_mk1/gh-pages/assets/ableton-komplete-kontrol.jpg)

## Features

* **Adds automatic Ableton device encoder support.** This means that when a device is focused (it has the blue hand icon), the 8 encoder knobs on the keyboard automatically map to the macro controls.
* **Adds fader support for Master and 7 more tracks.** This allows easy track volume adjustment and mixing directly from your controller.
* **Changes the Loop button to instead activate Session Record.** The transport controls are incomplete, and I decided easy activation of this setting was more important.
* **Adjusts the track selection algorithm.** I found the way that the controller's arrow keys function to be too idiosyncratic and wanted to change it. The behavior is as follows:
  * Navigating left or right will select the currently selected/focused track if it's not already armed.
  * Navigating will select the next track in the chosen direction if the previous track was already armed.
  * ‎Navigating past the end of the list of tracks has no effect.

* ‎**See Advanced Features below.**

## Installation

* Download a copy of this repo from the Releases page.
* ‎Close any running copies of Ableton Live.
* Unpack the contents of the archive into your Ableton `MIDI Remote Scripts` folder, using the same location as [in the documentation](https://support.native-instruments.com/hc/en-us/articles/209557689).
* Using Controller Editor, create configuration pages for the encoder knobs:
  1. Devices - ![devices configuration screenshot](https://raw.githubusercontent.com/bosgood/ableton_komplete_kontrol_mk1/gh-pages/assets/controller-editor-devices-screenshot.png)
    1. Name=DEV1, Type=Control Change, Channel=1, Number=22, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV2, Type=Control Change, Channel=1, Number=23, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV3, Type=Control Change, Channel=1, Number=24, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV4, Type=Control Change, Channel=1, Number=25, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV5, Type=Control Change, Channel=1, Number=26, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV6, Type=Control Change, Channel=1, Number=27, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV7, Type=Control Change, Channel=1, Number=28, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=DEV8, Type=Control Change, Channel=1, Number=29, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
  1. Faders - ![faders configuration screenshot](https://raw.githubusercontent.com/bosgood/ableton_komplete_kontrol_mk1/gh-pages/assets/controller-editor-faders-screenshot.png)
    1. Name=MASTER, Type=Control Change, Channel=1, Number=30, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK1, Type=Control Change, Channel=1, Number=31, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK2, Type=Control Change, Channel=1, Number=32, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK3, Type=Control Change, Channel=1, Number=33, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK4, Type=Control Change, Channel=1, Number=34, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK5, Type=Control Change, Channel=1, Number=35, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK6, Type=Control Change, Channel=1, Number=36, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
    1. Name=TRACK7, Type=Control Change, Channel=1, Number=37, Mode=Absolute, RangeFrom=0, RangeTo=127, Display=Unipolar
* ‎Start Ableton Live
* ‎In Preferences > MIDI, fill in 2 rows: one for the Komplete Kontrol DAW device (`Komplete Kontrol Mk1 DAW`), and one for the Komplete Kontrol MIDI keyboard input (`Komplete Kontrol Mk1 MIDI`). Assign the `Komplete Kontrol DAW - 1` and `KOMPLETE KONTROL S## (Port 1)` inputs and outputs to these control surfaces, respectively.

![screenshot showing Ableton MIDI configuration](https://raw.githubusercontent.com/bosgood/ableton_komplete_kontrol_mk1/gh-pages/assets/ableton-midi-preferences-screenshot.png)

## Advanced Features

* **MIDI source track support.** When arming a track, if it's name contains `[M]`, this is a hint to also arm the "MIDI source" track (its label must contain `[MIDISRC]`). This is to allow using a Komplete Kontrol instance's Scale feature while actually playing an Ableton, or at least non-KK track. N.B.: `MIDISRC` should not have any sound output assigned to it. This is most efficiently accomplished by using a KK instance that loads an empty Reaktor instance, which won't consume much CPU.

Ableton controls will not be active when a KK instance is selected (use Shift+Instance on the controller to toggle).

## Future Improvements/TODO

* Figure out a way to hijack the righthand side controls (Browse, Instance, etc). These seem to be on a different controller and aren't communicating through Ableton's `ControlSurface` API.
* ‎Is it possible to have the track selection arrow buttons work without first placing a KK instance on a track? That would be great.
* Figure out a way to allow custom encoder CC values to be easily MIDI-mapped. Can this be done without more code?
* Support for the Komplete Kontrol MK2. I don't have one, so I don't know what it's missing (if anything), but I'd be more than happy to reimplement this or something similar if I were sent one!
* Suggestions and PRs welcome!

## Questions?

Your question may already have been answered in the [original announcement post](https://www.reddit.com/r/NativeInstruments/comments/75azdz/ableton_komplete_kontrol_mk1_advanced_integration/). Otherwise feel free to DM me on [Reddit](https://www.reddit.com/user/bosgood/) for help.
