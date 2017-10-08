import Live
RecordingQuantization = Live.Song.RecordingQuantization

#For Global Debug Output
msg_sender = None

def register_sender(sender):
    global msg_sender
    msg_sender = sender

def debug_out(message):
    msg_sender.log_message(message) 

