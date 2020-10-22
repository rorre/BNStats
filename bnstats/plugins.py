from starlette.templating import Jinja2Templates
from webassets import Bundle
from webassets import Environment as AssetsEnvironment
from webassets.ext.jinja2 import AssetsExtension

assets_env = AssetsEnvironment("./bnstats/static", "/static")
templates = Jinja2Templates(directory="bnstats/templates")
templates.env.add_extension(AssetsExtension)
templates.env.assets_environment = assets_env

js_bundle = Bundle(
    Bundle(
        "js/vendor/jquery.js",
        "js/vendor/semantic.js",
        "js/vendor/tablesort.js",
        "js/vendor/chart.js",
    ),
    Bundle(
        "js/filter.js",
        "js/profile.js",
        "js/table.js",
    ),
    filters="rjsmin",
    output="bundle.%(version)s.js",
)
css_bundle = Bundle("css/*.css", filters="rcssmin", output="bundle.%(version)s.css")
assets_env.register("js_all", js_bundle)
assets_env.register("css_all", css_bundle)
