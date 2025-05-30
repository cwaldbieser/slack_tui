###########
 Slack TUI
###########

A terminal user interface for interacting with Slack.

*************************
 Deploying the Slack App
*************************

In order to use these terminal tools, you must first deploy a Slack app
to a workspace. The file ``manifest.yml`` can be imported. Browse to
https://api.slack.com/apps . Choose "Create New App" and select the
"From an app manifest" option. Follow the instructions to import the
app.

This process will grant permissions and event subscriptions to the app
that the terminal tools will need.

At the end of the process, you should have the tokens you need to grant
your app the required permissions. You will need both an App token and a
User token.

The App token can be found under your App's "Basic Information"
settings, in the section "App-Level Tokens". This token has the Slack
``connections:write`` permission, that allows the terminal tools to use
"Socket Mode". Socket Mode uses websockets rather than public HTTPS
endpoints to connect to the Slack APIs.

The User token can be found in the "Oauth & Permissions" feature for
your App, in the section "OAuth Tokens for Your Workspace".

These tokens need to be included in you workspace configuration file--
``$HOME/.config/slacktui/$WORKSPACE.toml``.

*********
 Scripts
*********

The script ``event_collector.py`` is meant to be run non-interactively.
It receives events from a Slack workspace and records those in a local
sqlite database.

The ``slack_tui.py`` script is an interactive terminal user interface
(TUI). This program lets you view messages in channels and DMs as well
as allowing you to post your own messages.
