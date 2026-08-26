from chimerax.core.toolshed import BundleAPI


class _FigureStyleAPI(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        from .tool import FigureStyleTool
        return FigureStyleTool(session, ti.name)

    @staticmethod
    def register_command(bi, ci, logger):
        from . import commands  # registration happens as an import side effect

    @staticmethod
    def run_provider(session, name, mgr, **kw):
        if name == "figurestyle_toolbar":
            from chimerax.core.commands import run
            run(session, 'ui tool show "FigureStyle"')


bundle_api = _FigureStyleAPI()
