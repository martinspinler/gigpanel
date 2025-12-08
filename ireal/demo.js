// global document, window

window.addEventListener("load", async () => {

	var playlist;
	var options = {
		minor: "minus",
		transpose: 0,
		useH: false,
		hilite: true
	};
	
	function makePlaylist(text) {
		playlist = new Playlist(text);
		window.playlist = playlist
		var lbHtml = "";
		var chordsHtml = "";
		for (var i = 0; i < playlist.songs.length; i++) {
			lbHtml += `<option value="${i}">${playlist.songs[i].title}</option>`;
			chordsHtml += `<div id="song-${i}"></div>`;
		}
		document.getElementById("songs").innerHTML = lbHtml;
		document.getElementById("chords").innerHTML = chordsHtml;
	}
	
	/**
	* Render a song into the container "#song-index".
	* @param {int} index - the song index
	*/
	function renderSong(index) {
		var song = playlist.songs[index];
		var r = new iRealRenderer;
		r.parse(song);
		song = r.transpose(song, options);
		var container = document.getElementById("song-" + index);
		container.innerHTML = `<h3>${song.title} (${song.key
			.replace(/b/g, "\u266d")
			.replace(/#/g, "\u266f")})</h3><h5>${song.composer}</h5>`;
		r.render(song, container, options);			
	}
	
	function renderSelected() {
		var selected = document.getElementById("songs").options;
		selected = [...selected].filter(option => option.selected).map(el => +el.value);
		for (var i = 0; i < playlist.songs.length; i++) {
			if (selected.includes(i))
				renderSong(i);
			else
				document.getElementById(`song-${i}`).innerHTML = "";
		}
	}

	function renderIndex(index) {
		for (var i = 0; i < playlist.songs.length; i++) {
			if (i == index)
				renderSong(i);
			else
				document.getElementById(`song-${i}`).innerHTML = "";
		}
	}

	document.getElementById("songs").addEventListener("change", () => renderSelected());
	
	document.querySelectorAll('[name="minor"]').forEach(el => {
		el.addEventListener("click", (ev) => {
			var mode = ev.target.id;
			options.minor = mode;
			renderSelected();
		});
	});

	document.getElementById("ui-useh").addEventListener("click", ev => {
		options.useH = ev.target.checked;
		renderSelected();
	});

	document.getElementById("ui-hilite").addEventListener("click", ev => {
		options.hilite = ev.target.checked;
		renderSelected();
	});

	document.getElementById("ui-transpose").addEventListener("input", ev => {
		options.transpose = +ev.target.value;
		renderSelected();
	});
	document.getElementById("ui-transpose").addEventListener("change", ev => {
		options.transpose = +ev.target.value;
		renderSelected();
	});

	document.getElementById("ui-fontsize").addEventListener("input", ev => {
		document.getElementById("chords").style.fontSize = ev.target.value + "pt";
	});
	document.getElementById("ui-fontsize").addEventListener("change", ev => {
		document.getElementById("chords").style.fontSize = ev.target.value + "pt";
	});

	document.getElementById("ui-file").addEventListener("change", ev => {
		var f = ev.target.files[0];
		var reader = new FileReader();
		reader.addEventListener("loadend", () => {
			if (reader.error)
				alert(`Cannot read file ${f.name}: ${reader.error}`);
			else
				makePlaylist(reader.result);
		});
		reader.readAsText(f, "utf-8");
	});

	window.makePlaylist = makePlaylist;
	window.renderSong = renderIndex;

});
