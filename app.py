from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")


# Store active rooms and user mappings
rooms = {}  # {room_id: [sid_list]}
user_rooms = {}  # {sid: room_id}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')
    # Clean up user from rooms
    if request.sid in user_rooms:
        room_id = user_rooms[request.sid]
        if room_id in rooms and request.sid in rooms[room_id]:
            rooms[room_id].remove(request.sid)
            logger.info(f'User {request.sid} removed from room {room_id}')
            emit('user_left', {'userId': request.sid}, room=room_id)
            if len(rooms[room_id]) == 0:
                del rooms[room_id]
                logger.info(f'Room {room_id} deleted (empty)')
        del user_rooms[request.sid]
        leave_room(room_id)
        emit('room_left', {'roomId': room_id}, to=request.sid)

@socketio.on('create_room')
def handle_create_room(data):
    room_id = data.get('roomId')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    if room_id not in rooms:
        rooms[room_id] = []
    if request.sid not in rooms[room_id]:
        rooms[room_id].append(request.sid)
        user_rooms[request.sid] = room_id
        join_room(room_id)
        logger.info(f'Room created: {room_id} by {request.sid}')
        emit('room_created', {'roomId': room_id}, to=request.sid)

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('roomId')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    if room_id in rooms:
        if request.sid not in rooms[room_id]:
            rooms[room_id].append(request.sid)
            user_rooms[request.sid] = room_id
            join_room(room_id)
            logger.info(f'User {request.sid} joined room {room_id}')
            emit('room_joined', {'roomId': room_id}, to=request.sid)
            emit('user_joined', {'userId': request.sid}, room=room_id, include_self=False)
    else:
        emit('error', {'message': 'Room does not exist'})

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('roomId')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    if room_id in rooms and request.sid in rooms[room_id]:
        rooms[room_id].remove(request.sid)
        if len(rooms[room_id]) == 0:
            del rooms[room_id]
            logger.info(f'Room {room_id} deleted (empty)')
        if request.sid in user_rooms:
            del user_rooms[request.sid]
        leave_room(room_id)
        logger.info(f'User {request.sid} left room {room_id}')
        emit('room_left', {'roomId': room_id}, to=request.sid)
        emit('user_left', {'userId': request.sid}, room=room_id)

@socketio.on('comment')
def handle_comment(data):
    room_id = data.get('roomId')
    username = data.get('username')
    message = data.get('message')
    
    if not room_id or not username or not message:
        emit('error', {'message': 'Create a room first'})
        return
    
    if room_id in rooms and request.sid in rooms[room_id]:
        logger.info(f'Comment in room {room_id} by {username}: {message}')
        emit('comment', {
            'username': username,
            'message': message
        }, room=room_id)
    else:
        emit('error', {'message': 'Not in room or room does not exist'})

@socketio.on('offer')
def handle_offer(data):
    room_id = data.get('roomId')
    if room_id in rooms and request.sid in rooms[room_id]:
        emit('offer', {
            'sdp': data.get('sdp'),
            'userId': request.sid
        }, room=room_id, include_self=False)
    else:
        emit('error', {'message': 'Not in room or room does not exist'})

@socketio.on('answer')
def handle_answer(data):
    room_id = data.get('roomId')
    if room_id in rooms and request.sid in rooms[room_id]:
        emit('answer', {
            'sdp': data.get('sdp'),
            'userId': request.sid
        }, room=room_id, include_self=False)
    else:
        emit('error', {'message': 'Not in room or room does not exist'})

@socketio.on('candidate')
def handle_candidate(data):
    room_id = data.get('roomId')
    if room_id in rooms and request.sid in rooms[room_id]:
        emit('candidate', {
            'candidate': data.get('candidate'),
            'userId': request.sid
        }, room=room_id, include_self=False)
    else:
        emit('error', {'message': 'Not in room or room does not exist'})

@socketio.on('ping')
def handle_ping():
    emit('pong')

@app.route('/templates/index.html')
def serve_template():
    return render_template('index.html')

@app.route('/templates')
def templates():
    return {
        'index.html': render_template('index.html')
    }

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=True, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)