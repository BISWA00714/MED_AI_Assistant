from flask_socketio import SocketIO, emit, join_room, leave_room
import json

# Initialize SocketIO without binding to an app immediately
socketio = SocketIO(cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print("New WebSocket client connected!")

@socketio.on('join')
def on_join(data):
    """
    Clients join a specific room when they connect.
    For doctors, they join the 'doctors' room to receive broadcast alerts.
    For chat, patients and doctors join a dedicated session room ('session_<id>').
    """
    room = data.get('room')
    if room:
        join_room(room)
        print(f"User securely joined room: {room}")

@socketio.on('emergency_alert')
def handle_emergency(data):
    """
    Receives an emergency payload from a patient and instantly broadcasts it to all connected doctors.
    """
    print(f"EMERGENCY TRIGGERED: {data}")
    emit('emergency_broadcast', data, room='doctors')

@socketio.on('chat_message')
def handle_chat_message(data):
    """
    Routes a private chat message between a doctor and patient in their dedicated room.
    """
    room = data.get('room')
    if room:
        emit('receive_message', data, room=room)
