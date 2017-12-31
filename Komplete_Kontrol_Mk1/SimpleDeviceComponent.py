from _Framework.DeviceComponent import DeviceComponent
from _Framework.ChannelTranslationSelector import ChannelTranslationSelector
from GUtil import debug_out

'''
Created on 18.08.2012

Extends Frameworks Device Comonent to a Listener

@author: Eric Ahrens


'''
    
class SimpleDeviceComponent(DeviceComponent):
    
    __doc__ = ' Class representing a device in Live '
    def __init__(self):
        DeviceComponent.__init__(self)
        self._control_translation_selector = ChannelTranslationSelector(8)
        
    def set_device(self, device):
        DeviceComponent.set_device(self, device)
        if device:
            #debug_out(" Device Set " + str(device.name) + " Class: " + str(device.class_name) 
            #          + " DisplayName: " + str(device.class_display_name) + " Type: " + str(device.type))
            vparm = device.parameters
            #for p in vparm:
            #    debug_out(" > " + str(p.name) + " : " + str(p.original_name))
        
    def disconnect(self):
        self._control_translation_selector.disconnect()
        DeviceComponent.disconnect(self)
        return None

        
