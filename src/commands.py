from chimerax.core.commands import CmdDesc, register, StringArg


def figurestyle_apply(session, name):
    from .style_model import load_templates
    templates = {t.name: t for t in load_templates()}
    if name not in templates:
        session.logger.error(f"FigureStyle: no template named '{name}'")
        return
    from chimerax.core.commands import run
    t = templates[name].resolve_for_session(session)
    for cmd in t.to_cxc():
        run(session, cmd)


desc = CmdDesc(required=[("name", StringArg)], synopsis="Apply a FigureStyle template")
register("figurestyle apply", desc, figurestyle_apply)
