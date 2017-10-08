#__init__.py
from FocusControl import FocusControl, log, DEVICE_ROLE_DAW, DEVICE_ROLE_MIDI_KEYBOARD


def create_instance(c_instance):
    log('Komplete_Kontrol creating instance')
    return FocusControl(c_instance, DEVICE_ROLE_DAW)


from _Framework.Capabilities import *


def get_capabilities():
    return {
        CONTROLLER_ID_KEY: controller_id(vendor_id=9000, product_ids=[
            2], model_name='Focus Control'),
        PORTS_KEY: [inport(props=[HIDDEN, NOTES_CC, SCRIPT]),
                    inport(props=[]),
                    outport(props=[HIDDEN,
                                   NOTES_CC,
                                   SYNC,
                                   SCRIPT]),
                    outport(props=[])]}
