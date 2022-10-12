from lona.html import Widget, HTML

#from .static_files import STATIC_FILES
from lona.static_files import StaticFile, StyleSheet, Script, SORT_ORDER


class Offcanvas(Widget):
    STATIC_FILES = [
        Script(
            name='mybootstrap5.widgets',
            path='static/mybootstrap5-widgets.js',
            url='mybootstrap5-widgets.js',
            sort_order=SORT_ORDER.LIBRARY,
        ),
    ]
    FRONTEND_WIDGET_CLASS = 'mybootstrap5.Offcanvas'

    def __init__(self, _id):
        self.nodes = HTML(f"""
            <div class="modal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"></h5>
                            <button type="button" class="btn-close" aria-label="Close"></button>
                        </div>
                        <div class="modal-body"></div>
                        <div class="modal-footer"></div>
                    </div>
                </div>
            </div>
        """)[0]  # NOQA

        self.nodes = HTML(f"""
<div class="offcanvas offcanvas-end" tabindex="-1" id="{_id}" aria-labelledby="offcanvasExampleLabel">
  <div class="offcanvas-header">
    <h5 class="offcanvas-title">Offcanvas</h5>
    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" data-bs-target="#{_id}" aria-label="Close"></button>
  </div>
  <div class="offcanvas-body">
  </div>
</div>""")[0]  # NOQA

        self._title = self.query_selector('h5.offcanvas-title')
        self._body = self.query_selector('div.offcanvas-body')

        # setup data
        self.data = {
            'modal_options': {
                'focuse': True,
            },
            'visible': False,
        }

    # methods #################################################################
    def hide(self):
        self.data['visible'] = False

    def show(self):
        self.data['visible'] = True

    def set_title(self, *nodes):
        self._title.nodes = list(nodes)

    def set_body(self, *nodes):
        self._body.nodes = list(nodes)
