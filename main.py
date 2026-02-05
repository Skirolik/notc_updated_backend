from app import create_app,socketio

app=create_app()

if __name__ == '__main__':
    socketio.init_app(app)
    socketio.run(app,host='0.0.0.0',port=5054,debug=False,allow_unsafe_werkzeug=True)