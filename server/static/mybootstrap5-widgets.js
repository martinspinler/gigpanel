function Bootstrap5Offcanvas(lona_window) {
    this.lona_window = lona_window;

    this._update = function() {
        if(this.data.visible) {
            this.modal.show();
        } else {
            this.modal.hide();
        };
    };

    this.setup = function() {
        this.modal = new bootstrap.Offcanvas(
            this.nodes[0],
            this.data.modal_options,
        );
        if(this.data.visible) {
			this.nodes[0].classList.add('show')
		};

        this._update();
    };

    this.deconstruct = function() {
        this.modal.dispose();
    };

    this.data_updated = function() {
        this._update();
    };
};

Lona.register_widget_class('mybootstrap5.Offcanvas', Bootstrap5Offcanvas);
