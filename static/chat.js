

//function $(x) { return document.getElementById(x) };
//var $ = document.querySelectorAll.bind(document);
var $ = document.getElementById.bind(document);

document.addEventListener("DOMContentLoaded", function() {
	if (!window.console) window.console = {};
	if (!window.console.log) window.console.log = function() {};
	
	$('messageform').addEventListener("submit", function(e) {
		e.preventDefault();
	});

	$('sendbutton').addEventListener("click", function() {
		newMessage( $('messageform'));
		return false;
	});
	$("messageform").addEventListener("keypress", function(e) {
		if (e.keyCode == 13) {
			newMessage( $('messageform'));
			return false;
		}
	});
	$("message").select();
	updater.start();
});

function newMessage(form) {
	var message = {};
	message.body = $('message').value;
	message.room = "General";
	updater.socket.send(JSON.stringify(message));
	$('message').value = "";
}

var formToDict = function(thiss) {
	var fields = thiss.serializeArray();
	var json = {}
	for (var i = 0; i < fields.length; i++) {
		json[fields[i].name] = fields[i].value;
	}
	if (json.next) delete json.next;
	return json;
};

var updater = {
	socket: null,

	start: function() {
		var url = "ws://" + location.host + "/chatsocket";
		updater.socket = new WebSocket(url);
		updater.socket.onmessage = function(event) {
			var jdata = JSON.parse(event.data);
			if (jdata["add_room"] != null) {
				console.log("Got room");
				
				// Add the room
				var room = document.createElement("div");
				room.id = "room-" + jdata["add_room"];
				$("inbox").append(room);
				
				//room.style.display = "none";//hides the room
				
				// Need to also add room links
			}
			else {
				updater.showMessage(jdata);
			}
		}
	},

	showMessage: function(message) {
		var existing = $("m" + message.id);
		if (existing != null) return;
		
		var node = document.createElement("div");
		node.class = "message";
		node.id = 'm' + message.id;
		
		// Format time and actually add the message
		var date = new Date(0);
		date.setUTCSeconds(parseFloat(message.time));
		var time_str = date.getHours().toString();
		if (date.getMinutes() < 10) {
			time_str += ":0" + date.getMinutes().toString();
		}
		else {
			time_str += ":" + date.getMinutes().toString();
		}
		node.innerHTML = '<span class="time">' + time_str +
						 "</span> - " + '<span class="name">' + message.user +
						 "</span>" + ": " + message.html;
						 
		// look for an image in the message body 
		// if we see it, add an image tag for it
		var pat = /http[\w\d://.-]+((.jpg)|(.png)|(.jpeg)|(.gif))/g;
		var val = pat.exec(message.body);
		console.log(val);
		if (val) {	
			node.innerHTML += '<div/><img class="embed_img" src="'
								+ val[0] + '" height="200" width="200">';
		}
		
		$("room-"+message.room).append(node);
	}
};
