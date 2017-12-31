from __future__ import with_statement

import sys
import socket
import Live

from _Framework.SubjectSlot import subject_slot
from SimpleDeviceComponent import SimpleDeviceComponent
from GUtil import debug_out, register_sender
from _Generic import GenericScript
from _Generic.SpecialMixerComponent import SpecialMixerComponent

from _Framework import Task
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.ButtonElement import ButtonElement, ON_VALUE, OFF_VALUE
from _Framework.TransportComponent import TransportComponent
from _Framework.EncoderElement import EncoderElement

import MidiRemoteScript


'''
Created on 13.10.2013
@author: Eric Ahrens
'''

DEVICE_ROLE_DAW = 'KOMPLETE_KONTROL_DAW'
DEVICE_ROLE_MIDI_KEYBOARD = 'KOMPLETE_KONTROL_MIDI_KEYBOARD'

GLOBAL_CHANNEL = 0

BUTTON_STATE_OFF = 0
BUTTON_STATE_ON = 127
BUTTON_PRESSED = 1
BUTTON_RELEASED = 0

SID_FIRST = 0
SID_NAV_LEFT = 20
SID_NAV_RIGHT = 21
SID_TRANSPORT_LOOP = 86
SID_TRANSPORT_REWIND = 91
SID_TRANSPORT_FAST_FORWARD = 92
SID_TRANSPORT_STOP = 93
SID_TRANSPORT_PLAY = 94
SID_TRANSPORT_RECORD = 95
SID_LAST = 112
transport_control_switch_ids = {
    SID_TRANSPORT_LOOP: 'LOOP',
    SID_TRANSPORT_REWIND: 'REWIND',
    SID_TRANSPORT_FAST_FORWARD: 'FAST_FORWARD',
    SID_TRANSPORT_STOP: 'STOP',
    SID_TRANSPORT_PLAY: 'PLAY',
    SID_TRANSPORT_RECORD: 'RECORD',
}

PARAM_PREFIX = 'NIKB'
PLUGIN_PREFIX = 'Komplete Kontrol'
PLUGIN_CLASS_NAME_VST = 'PluginDevice'
PLUGIN_CLASS_NAME_AU = 'AuPluginDevice'

ENCODER_CCS = (range(22, 30))
MASTER_VOLUME_CC = 30
VOLUME_CCS = tuple(range(31, 38))

ABSOLUTE_MAP_MODE = Live.MidiMap.MapMode.absolute


def log(message):
    sys.stderr.write("LOG: " + str(message).encode("utf-8"))


def device_info(device):
    if device:
        debug_out("  # " + str(device.name) + " Class: " + str(device.class_name)
                  + " DisplayName: " + str(device.class_display_name) + " Type: " + str(device.type))


def vindexof(alist, element):
    index = 0
    for ele in alist:
        if ele == element:
            return index
        index = index + 1
    return None


def arm_smart(song, track=None):
    if not track:
        track = song.view.selected_track
    if track and track.can_be_armed and not track.arm:
        tracks = song.tracks

        # Determine if selected track requires a MIDI source
        use_midi_src = False
        if '[M]' in track.name:
            use_midi_src = True

        for songtrack in tracks:
            # Detect and arm the MIDI source track
            if use_midi_src and '[MIDISRC]' in songtrack.name:
                songtrack.arm = True
            elif songtrack != track and songtrack and songtrack.can_be_armed and songtrack.arm:
                songtrack.arm = False

        track.arm = True

# -------------------------------------------------------------------------------------------
# TrackElement


class TrackElement:

    allow_activate_track = False

    def __init__(self, index, track, receiver, *a, **k):
        self.index = index
        self.track = track

        if receiver.device_role == DEVICE_ROLE_DAW:
            if track.can_be_armed:
                debug_out("Track can be armed: %s, %s" %
                          (track.name, str(track)))
                self.allow_activate_track = True
                track.add_arm_listener(self._changed_arming)
                track.add_implicit_arm_listener(self._changed_implicit_arming)
            else:
                debug_out("Track cannot be armed: %s, %s" %
                          (track.name, str(track)))

        track.add_devices_listener(self._changed_devices)

        self.receiver = receiver

    def _changed_implicit_arming(self):
        debug_out("_changed_implicit_arming called on: %s, %s" %
                  (self.track.name, str(self.track)))
        self._handle_track_armed()

    def _changed_arming(self):
        debug_out(" _changed_arming() called")
        self._handle_track_armed()

    def _handle_track_armed(self):
        if not self.track.arm and not self.track.implicit_arm:
            self.receiver.deactivate_track(self.index, self.track)
        elif self.allow_activate_track and (self.track.arm or self.track.implicit_arm):
            self.receiver.control_track(self.index, self.track)

    def _changed_devices(self):
        if self.allow_activate_track:
            self.receiver.devices_changed(self.index, self.track)

    def release(self):
        if self.track and self.track.can_be_armed:
            self.track.remove_arm_listener(self._changed_arming)
            self.track.remove_implicit_arm_listener(
                self._changed_implicit_arming)
        if self.track:
            self.track.remove_devices_listener(self._changed_devices)
        self.receiver = None
        self.track = None


# -------------------------------------------------------------------------------------------
# FocusControl

class FocusControl(ControlSurface):

    controlled_track = None

    def __init__(self, c_instance, device_role):
        super(FocusControl, self).__init__(c_instance)
        self.song().add_is_playing_listener(self.__update_play_button_led)
        self.device_role = device_role

        register_sender(self)  # For Debug Output only

        debug_out(str(dir(self)))
        self._active = False
        self._tracks = []
        self.rewind_button_down = False
        self.forward_button_down = False

        with self.component_guard():
            self._set_suppress_rebuild_requests(True)
            self._suppress_send_midi = True

            device = SimpleDeviceComponent(
                device_selection_follows_track_selection=True)
            device.name = 'Device_Component'
            self.set_up_encoders(device)
            self.set_up_mixer_component(
                VOLUME_CCS, (), {
                    'NUMSENDS': 0,
                    'MASTERVOLUME': MASTER_VOLUME_CC,
                    'NOTOGGLE': 0
                }, GLOBAL_CHANNEL, ABSOLUTE_MAP_MODE)
            self.set_device_component(device)

            self._on_selected_track_changed()
            self.set_up_controls()
            self.request_rebuild_midi_map()

            self._set_suppress_rebuild_requests(False)
            self._active = True
            self._suppress_send_midi = False

            if self.device_role == DEVICE_ROLE_DAW:
                # Transport controls - instantiate a TransportComponent. The default behavior when setting transport buttons
                # works well for most buttons, but not the stop button (since default for stop button is never lighting up)
                # so that one is handled manually.
                self.transport = TransportComponent()
                # ButtonElement(is_momentary, msg_type, channel, identifier)
                self.transport.set_play_button(ButtonElement(
                    False, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_PLAY))
                self.transport.set_record_button(ButtonElement(
                    False, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_RECORD))
                self.transport.set_seek_buttons(ButtonElement(True, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_FAST_FORWARD), ButtonElement(
                    True, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_REWIND))
                # self.transport.set_loop_button(ButtonElement(
                #     False, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_LOOP))
                self.transport.set_overdub_button(ButtonElement(
                    False, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_LOOP))

        self._assign_tracks()
        ctrack = self.get_controlled_track()
        if ctrack:
            track = ctrack[0]
            instr = ctrack[1]
            self.controlled_track = track
            index = list(self.song().tracks).index(track)
            self.update_status_midi(index, track, instr, 1)

        self.refresh_state()

    def refresh_state(self):
        self.__update_play_button_led()

    def receive_midi(self, midi_bytes):
        midi_status = midi_bytes[0] & 240
        debug_out("receive_midi() called: %s (note_on=%s, note_off=%s)" % (
            str(midi_status), MIDI_NOTE_ON_STATUS, MIDI_NOTE_OFF_STATUS))
        if midi_status == MIDI_NOTE_ON_STATUS or midi_status == MIDI_NOTE_OFF_STATUS:
            note = midi_bytes[1]
            value = BUTTON_PRESSED if midi_bytes[2] > 0 else BUTTON_RELEASED
            debug_out("midi note received: note=%s, value=%s" %
                      (note, value))
            if note in transport_control_switch_ids:
                if self.device_role == DEVICE_ROLE_DAW:
                    debug_out("transport received: note=%s, value=%s, transport=%s" % (
                        note, value, transport_control_switch_ids[note]))
                    self.handle_transport_switch_ids(note, value)
                else:
                    debug_out("transport ignored: note=%s, value=%s, transport=%s" % (
                        note, value, transport_control_switch_ids[note]))
                    return

        super(FocusControl, self).receive_midi(midi_bytes)

    def handle_transport_switch_ids(self, switch_id, value):
        #debug_out("handle_transport_switch_ids() called. switch_id: " + str(switch_id) + " value: " + str(value))
        if switch_id == SID_TRANSPORT_REWIND:
            if value == BUTTON_PRESSED:
                self.rewind_button_down = True
            elif value == BUTTON_RELEASED:
                self.rewind_button_down = False
            self.__update_forward_rewind_leds()

        elif switch_id == SID_TRANSPORT_FAST_FORWARD:
            if value == BUTTON_PRESSED:
                self.forward_button_down = True
            elif value == BUTTON_RELEASED:
                self.forward_button_down = False
            self.__update_forward_rewind_leds()

        elif self.device_role == DEVICE_ROLE_DAW and switch_id == SID_TRANSPORT_STOP and value == BUTTON_PRESSED:
            self.__stop_song()

    def __stop_song(self):
        self.song().stop_playing()
        self.__update_play_button_led()

    def __update_play_button_led(self):
        #debug_out("__update_play_button_led is called: is_playing: " + str(self.song().is_playing))
        if self.song().is_playing:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_PLAY, BUTTON_STATE_ON))
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_STOP, BUTTON_STATE_OFF))
        else:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_PLAY, BUTTON_STATE_OFF))
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_STOP, BUTTON_STATE_ON))

    def __update_forward_rewind_leds(self):
        if self.forward_button_down:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_FAST_FORWARD, BUTTON_STATE_ON))
        else:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_FAST_FORWARD, BUTTON_STATE_OFF))
        if self.rewind_button_down:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_REWIND, BUTTON_STATE_ON))
        else:
            self._send_midi(
                (MIDI_NOTE_ON_STATUS, SID_TRANSPORT_REWIND, BUTTON_STATE_OFF))

    def set_up_controls(self):
        is_momentary = True
        self.left_button = ButtonElement(
            is_momentary, MIDI_CC_TYPE, 0, SID_NAV_LEFT)
        self.right_button = ButtonElement(
            is_momentary, MIDI_CC_TYPE, 0, SID_NAV_RIGHT)
        self._do_left.subject = self.left_button
        self._do_right.subject = self.right_button

        if self.device_role == DEVICE_ROLE_DAW:
            self.stop_button = ButtonElement(
                False, MIDI_NOTE_TYPE, 0, SID_TRANSPORT_STOP)
            self._do_stop.subject = self.stop_button

    def set_up_encoders(self, device):
        parameter_encoders = []
        encoder_ccs = ENCODER_CCS
        for cc in encoder_ccs:
            channel = GLOBAL_CHANNEL
            if cc in range(128) and channel in range(16):
                encoder = EncoderElement(
                    MIDI_CC_TYPE, channel, cc, ABSOLUTE_MAP_MODE)
                encoder.name = 'Device_Parameter_' + \
                    str(list(encoder_ccs).index(cc)) + '_Control'
                parameter_encoders.append(encoder)
                log('Encoder: %s, CC: %s, channel: %s' %
                    (encoder.name, cc, channel))

        if len(parameter_encoders) > 0:
            device.set_parameter_controls(tuple(parameter_encoders))
            log('Initialized %s encoders' % len(parameter_encoders))

    def set_up_mixer_component(self, volume_controls, trackarm_controls, mixer_options, global_channel, volume_map_mode):
        if volume_controls != None and trackarm_controls != None:
            num_strips = max(len(volume_controls), len(trackarm_controls))
            send_info = []
            momentary_buttons = False
            mixer = SpecialMixerComponent(num_strips)
            mixer.name = 'Mixer'
            mixer.master_strip().name = 'Master_Channel_Strip'
            mixer.selected_strip().name = 'Selected_Channel_Strip'
            if mixer_options != None:
                if 'MASTERVOLUME' in mixer_options.keys() and mixer_options['MASTERVOLUME'] in range(128):
                    encoder = EncoderElement(
                        MIDI_CC_TYPE, global_channel, mixer_options['MASTERVOLUME'], volume_map_mode)
                    encoder.name = 'Master_Volume_Control'
                    mixer.master_strip().set_volume_control(encoder)
                if 'NUMSENDS' in mixer_options.keys() and mixer_options['NUMSENDS'] > 0:
                    for send in range(mixer_options['NUMSENDS']):
                        key = 'SEND' + str(send + 1)
                        if not key in mixer_options.keys():
                            raise AssertionError
                        None.append(mixer_options[key])

                momentary_buttons = 'NOTOGGLE' in mixer_options.keys()
                next_bank_button = None
                prev_bank_button = None
                if 'NEXTBANK' in mixer_options.keys() and mixer_options['NEXTBANK'] in range(128):
                    next_bank_button = ButtonElement(
                        momentary_buttons, MIDI_CC_TYPE, global_channel, mixer_options['NEXTBANK'])
                    next_bank_button.name = 'Mixer_Next_Bank_Button'
                if 'PREVBANK' in mixer_options.keys() and mixer_options['PREVBANK'] in range(128):
                    prev_bank_button = ButtonElement(
                        momentary_buttons, MIDI_CC_TYPE, global_channel, mixer_options['PREVBANK'])
                    prev_bank_button.name = 'Mixer_Previous_Bank_Button'
                mixer.set_bank_buttons(next_bank_button, prev_bank_button)
            for track in range(num_strips):
                strip = mixer.channel_strip(track)
                strip.name = 'Channel_Strip_' + str(track)
                if track in range(len(volume_controls)):
                    channel = global_channel
                    cc = volume_controls[track]
                    if isinstance(volume_controls[track], (tuple, list)):
                        cc = volume_controls[track][0]
                        if volume_controls[track][1] in range(16):
                            channel = volume_controls[track][1]

                    if cc in range(128) and channel in range(16):
                        encoder = EncoderElement(
                            MIDI_CC_TYPE, channel, cc, volume_map_mode)
                        encoder.name = str(track) + '_Volume_Control'
                        strip.set_volume_control(encoder)

                if track in range(len(trackarm_controls)) and trackarm_controls[track] in range(128):
                    button = ButtonElement(
                        momentary_buttons, MIDI_CC_TYPE, global_channel, trackarm_controls[track])
                    button.name = str(track) + '_Arm_Button'
                    strip.set_arm_button(button)
                send_controls = []
                for send in send_info:
                    encoder = None
                    if track in range(len(send)):
                        channel = global_channel
                        cc = send[track]
                        if isinstance(send[track], (tuple, list)):
                            cc = send[track][0]
                            if send[track][1] in range(16):
                                channel = send[track][1]

                        if cc in range(128) and channel in range(16):
                            encoder = EncoderElement(
                                MIDI_CC_TYPE, channel, cc, volume_map_mode)
                            encoder.name = str(
                                track) + '_Send_' + str(list(send_info).index(send)) + '_Control'

                    send_controls.append(encoder)

                strip.set_send_controls(tuple(send_controls))

    @subject_slot('value')
    def _do_stop(self):
        self.__stop_song()

    @subject_slot('value')
    def _do_left(self, value):
        assert value in range(128)
        if value != 0:
            log('Navigating to selection left')
            self.navigate_midi_track(-1)

    @subject_slot('value')
    def _do_right(self, value):
        assert value in range(128)
        if value != 0:
            log('Navigating to selection right')
            self.navigate_midi_track(1)

    '''
    Selects next available Track. Values for direction are -1 going left
    and -1 for going left.
    '''

    def navigate_midi_track(self, direction):
        song = self.song()
        tracks = song.tracks
        seltrack = song.view.selected_track
        index = vindexof(tracks, seltrack)

        # If the new selection isn't yet armed, arm that before
        # moving
        if not seltrack.arm:
            arm_smart(song, song.view.selected_track)
            return

        # Replace with get_next_midi_track to select next available midi track
        # left or right
        nxttrack = self.get_next_track(direction, index, tracks)
        if nxttrack:
            song.view.selected_track = nxttrack
            arm_smart(song, nxttrack)
        else:
            arm_smart(song, seltrack)

    '''
    Selects next available armable Track. Values for direction are -1 going left
    and -1 for going left.
    '''

    def get_next_track(self, direction, index, tracks):
        pos = index
        if pos == None:
            pos = len(tracks)
        pos = pos + direction
        while pos >= 0 and pos < len(tracks):
            track = tracks[pos]
            if track.can_be_armed:
                return track
            pos = pos + direction
        return None

    '''
    Selects next available MIDI Track. Values for direction are -1 going left
    and -1 for going left.
    '''

    def get_next_midi_track(self, direction, index, tracks):
        pos = index
        if pos == None:
            pos = len(tracks)
        pos = pos + direction
        while pos >= 0 and pos < len(tracks):
            track = tracks[pos]
            # Looking for a special Device
            if track.can_be_armed and track.has_midi_input:
                return track
            pos = pos + direction
        return None

    '''
    Returns tuple (track, (device [,Instance No]))
    '''

    def get_controlled_track(self):
        armed_tracks = []
        tracks = self.song().tracks

        for track in tracks:
            if track.can_be_armed and (track.arm or track.implicit_arm):
                armed_tracks.append(track)

        if len(armed_tracks) == 1:
            return (armed_tracks[0], self.find_instrument_list(armed_tracks[0].devices))

        if len(armed_tracks) > 1:
            instr = self.find_instrument_ni(armed_tracks)
            if instr:
                return instr

            return self.find_instrument_any(armed_tracks)

        return None

    def find_instrument_ni(self, tracks):
        for track in tracks:
            instr = self.find_instrument_list(track.devices)
            if instr and instr[1] != None:
                return (track, instr)
        return None

    def find_instrument_any(self, tracks):
        for track in tracks:
            instr = self.find_instrument_list(track.devices)
            if instr:
                return (track, instr)
        return None

    def _assign_tracks(self):
        tracks = self.song().tracks

        for track in self._tracks:
            track.release()

        self._tracks = []

        for index in range(len(tracks)):
            self._tracks.append(TrackElement(index, tracks[index], self))

    def control_track(self, index, track):
        if self.controlled_track != track:
            self.controlled_track = track
            instr = self.find_instrument_list(track.devices)
            debug_out("CONTROL_TRACK(): " +
                      track.name + "   " + str(instr))
            if track.implicit_arm and not track.arm:
                debug_out("going to arm implicit_armed track")

            run_task = Task.run(
                lambda: self.activate_track(index, track, instr))
            task_seq = Task.sequence(Task.delay(1), run_task)
            self._tasks.add(task_seq)
        else:
            debug_out("Not re-activating controlled track %s" % track.name)

    def activate_track(self, index, track, instr):
        is_ni = instr is not None and instr[1] is not None
        debug_out("ACTIVATE_TRACK(): %s %s (%s)" %
                  (track.name, str(instr), "NI" if is_ni else "non-NI"))
        track.arm = True
        self.update_status_midi(index, track, instr, 1)

    def deactivate_track(self, index, track):
        debug_out("DEACTIVATE_TRACK called: %s" % track.name)
        instr = self.find_instrument_list(track.devices)
        self.update_status_midi(index, track, instr, 0)

        if self.controlled_track and self.controlled_track == track:
            self.controlled_track = None
            debug_out("NO Controlled Track ")

    def devices_changed(self, index, track):
        debug_out(" DEVICES_CHANGED() Track " + str(index) + " " + track.name)
        instr = self.find_instrument_list(track.devices)
        self.update_status_midi(index, track, instr, 1)

    def _on_track_list_changed(self):
        # This is called whenever the tracks are re-ordered, which we don't really need,
        # therefore i commented out self.update_status_midi() below. -kurt
        super(FocusControl, self)._on_track_list_changed()
        self._assign_tracks()
        ctrack = self.get_controlled_track()
        if ctrack:
            track = ctrack[0]
            instr = ctrack[1]
            debug_out("_ON_TRACK_LIST_CHANGED() called " + str(instr))
            if track != self.controlled_track:
                self.controlled_track = track
                index = list(self.song().tracks).index(track)
                debug_out(
                    "_ON_TRACK_LIST_CHANGED: current track is not controlled_track")
                #self.update_status_midi(index, track, instr, 1)
        elif self.controlled_track:  # No Armed Track with Instrument
            debug_out(" No More Controlled Track")
            self.controlled_track = None

    def _on_selected_track_changed(self):
        super(FocusControl, self)._on_selected_track_changed()
        self.set_controlled_track(self.song().view.selected_track)

        # Block below was commented out because focus only follows track
        # arming, not selection. -kurt

        # self._on_devices_changed.subject = self.song().view.selected_track
        # track = self.song().view.selected_track
        # debug_out(" Changed Selected Track " + track.name)
        # if track.can_be_armed and track.arm:
        #     self.controlled_track = track
        # instr = self.find_instrument_list(track.devices)
        # index = list(self.song().tracks).index(track)
        # self.update_status_midi(index, track, instr, 1)

    def broadcast(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not s:
            debug_out(" Could Not open Socket ")
        else:
            try:
                s.connect(('localhost', 60090))
                s.sendall('Hello, world')
                s.close()
            except:
                debug_out(" No Server ")

    @subject_slot('devices')
    def _on_devices_changed(self):
        #debug_out(" > Changed Device on selected Track ")
        self.scan_devices()

    def find_instrument_list(self, devicelist):
        for device in devicelist:
            instr = self.find_instrument(device)
            if instr:
                return instr
        return None

    def find_in_chain(self, chain):
        for device in chain.devices:
            instr = self.find_instrument(device)
            if instr:
                return instr
        return None

    def find_instrument(self, device):
        debug_out("find_instrument() called. type=%s, name=%s, class_name=%s, class_display_name=%s, parameters=%s" % (
            device.type, device.name, device.class_name, device.class_display_name, ','.join([p.name for p in device.parameters])))
        if device.type == 1:
            debug_out("find_instrument() found device type 1")
            if device.can_have_chains:
                chains = device.chains
                for chain in chains:
                    instr = self.find_in_chain(chain)
                    if instr:
                        return instr
            elif (device.class_name == PLUGIN_CLASS_NAME_VST or device.class_name == PLUGIN_CLASS_NAME_AU) and (device.class_display_name.startswith(PLUGIN_PREFIX)):
                device_params = device.parameters
                debug_out("find_instrument() found NI device")
                if device_params and len(device_params) > 1:
                    pn = device_params[1].name
                    debug_out("device_params[1].name=%s" % (pn,))
                    pnLen = len(pn)
                    if pn.startswith(PARAM_PREFIX):
                        #debug_out("pn[1] starts with " + PARAM_PREFIX + " and str(pn[4:pnLen]) = " + str(pn[4:pnLen]))
                        return (str(device.class_display_name), str(pn[4:pnLen]))
                else:
                    debug_out(
                        "insufficient device parameters. device attrs=%s" % str(dir(device)))
            return (device.class_display_name, None)
        return None

    def scan_chain(self, chain):
        for device in chain.devices:
            self.scan_device(device)

    def scan_device(self, device):
        #        if device.type == 1:
        #            debug_out("SNDDEV   " + device.name + " <"  + device.class_name + "> " + device.class_display_name + " (" + str(device.type) +")")

        if device.class_name == 'PluginDevice' and device.class_display_name == 'FocusTester1':
            parms = device.parameters
#            if parms and len(parms)>1:
#                debug_out("# Focus Device " + parms[1].name)

        elif device.can_have_chains:
            chains = device.chains
            for chain in chains:
                self.scan_chain(chain)

    def update_status_midi(self, index, track, instrument, value):
        #debug_out("UPDATE_STATUS(): track: "+track.name+" instr: "+str(instrument)+" value: "+str(value))
        msgsysex = [240, 0, 0, 102, 20, 18, 0]
        tr_name = track.name
        for c in tr_name:
            msgsysex.append(ord(c))
        msgsysex.append(25)
        ind_str = str(index)
        for c in ind_str:
            msgsysex.append(ord(c))
        if instrument != None:
            msgsysex.append(25)
            for c in instrument[0]:
                msgsysex.append(ord(c))
            if instrument[1] != None:
                msgsysex.append(25)
                for c in instrument[1]:
                    msgsysex.append(ord(c))
        # msgsysex.append(25)
        # msgsysex.append(value)
        msgsysex.append(247)
        self._send_midi(tuple(msgsysex))

    def send_to_display(self, text, grid=0):
        if(len(text) > 28):
            text = text[:27]

        msgsysex = [240, 0, 0, 102, 23, 18, min(grid, 3) * 28]
        filled = text.ljust(28)  # 27 Characters
        for c in filled:
            msgsysex.append(ord(c))
        msgsysex.append(247)
        self._send_midi(tuple(msgsysex))

    def scan_devices(self):
        song = self.song()
        for track in song.tracks:
            #debug_out(" Scan Track : " + str(track.name))
            for device in track.devices:
                self.scan_device(device)

    def disconnect(self):
        self._active = False
        self._suppress_send_midi = True
        self.song().remove_is_playing_listener(self.__update_play_button_led)
        super(FocusControl, self).disconnect()
        return None
