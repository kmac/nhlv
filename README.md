nhlv - NHL stream viewer
========================

`nhlv` is a command-line interface to the NHL.tv service. It's primary purpose is to allow you to view game
streams on linux, including live streams with a valid NHL tv/gamecenter subscription.  It also allows you to
view game status, results and schedules, stream highlights (recap and condensed games), and filter results
based on favourite teams.

Features:

* stream or record live or archived NHL games (requires NHL.tv subscription)
* show completed game highlights (condensed or recap) (no subscription required)
* display game schedules for given day or number of days
    - option to show or hide scores
* filter display based on favourite teams
* show standings


This project is inspired from the MLB baseball [MLBviewer](https://github.com/sdelafond/mlbviewer) project,
although it differs in that it does not provide an interactive interface (that may be added in future releases). 

This package requires a valid NHL.tv subscription in order to view live or archived games. It is also subject
to local blackout restrictions. However, if you don't have a subscription you can still view game recaps or
condensed games.


Sample console output:

````
       2017-12-28                                                | Score |   State   | Feeds
-----------------------------------------------------------------|-------|-----------|------------
Live Games:                                                      |       |           |
19:30: Boston Bruins (BOS) at Washington Capitals (WSH)          |  3-3  | End OT    | away, french, national
21:00: Toronto Maple Leafs (TOR) at Arizona Coyotes (ARI)        |  3-2  | 11:40 2nd | away, home
22:00: Chicago Blackhawks (CHI) at Vancouver Canucks (VAN)       |  0-1  | 11:26 1st | away, national
22:00: Vegas Golden Knights (VGK) at Los Angeles Kings (LAK)     |  0-0  | 20:00 1st | national
-----                                                            |       |           |
22:30: Calgary Flames (CGY) at San Jose Sharks (SJS)             |       |           | away, home
19:30: Montréal Canadiens (MTL) at Tampa Bay Lightning (TBL)     |  1-3  | Final     | away, french, home
19:30: Philadelphia Flyers (PHI) at Florida Panthers (FLA)       |  2-3  | Final     | away, home

````

Standings output:

````
   ======  Division  ======     W  OT L   P  Streak
   --- Eastern - Metropolitan ---
1  x-Washington Capitals        46  7 25  99 [L1]
2  x-Pittsburgh Penguins        45  6 28  96 [W2]
3  Columbus Blue Jackets        44  6 29  94 [OT1]
4  Philadelphia Flyers          39 14 25  92 [W1]
5  New Jersey Devils            41  9 28  91 [W1]
6  Carolina Hurricanes          35 11 33  81 [L1]
7  New York Rangers             34  9 36  77 [W1]
8  New York Islanders           32 10 37  74 [L2]
   --- Eastern - Atlantic ---
1  x-Boston Bruins              49 11 17 109 [W2]
2  x-Tampa Bay Lightning        52  4 22 108 [W1]
3  x-Toronto Maple Leafs        47  7 25 101 [L1]
4  Florida Panthers             39  8 30  86 [L1]
5  Detroit Red Wings            30 11 38  71 [W3]
6  Montréal Canadiens           28 12 38  68 [L1]
7  Ottawa Senators              27 11 40  65 [L1]
8  Buffalo Sabres               25 12 41  62 [W1]
   --- Western - Central ---
1  x-Nashville Predators        50 11 17 111 [L1]
2  x-Winnipeg Jets              48 10 20 106 [W1]
3  Minnesota Wild               43 10 25  96 [L1]
4  St. Louis Blues              43  6 29  92 [L1]
5  Colorado Avalanche           42  8 28  92 [W1]
6  Dallas Stars                 40  8 31  88 [W1]
7  Chicago Blackhawks           32 10 37  74 [L1]
   --- Western - Pacific ---
1  y-Vegas Golden Knights       50  7 22 107 [W2]
2  San Jose Sharks              44 10 25  98 [L2]
3  Los Angeles Kings            43  8 28  94 [OT1]
4  Anaheim Ducks                40 13 25  93 [W1]
5  Calgary Flames               36 10 33  82 [W1]
6  Edmonton Oilers              34  6 39  74 [L3]
7  Vancouver Canucks            30  9 40  69 [W4]
8  Arizona Coyotes              28 11 40  67 [W1]
````

This project incorporates some code modified from the following projects: 

* https://github.com/eracknaphobia/plugin.video.nhlgcl (Kodi plugin)
* https://github.com/NHLGames/nhl.py


## Pre-Requisites:

`nhlv` requires the following software to be installed and configured:

* python 
    - python v3 (tested with 3.6) 
* python modules (installed by `pip install`):
    - [requests](http://python-requests.org/) module 
    - [python-dateutil](https://dateutil.readthedocs.io/en/stable/) module
    - [python-lxml](http://lxml.de/) module
* [streamlink](https://streamlink.github.io/)
* a video player. Either `vlc` or `mpv` is recommended.
    - Note: player can be specified via config file. If player is not on the system path you may need to
      setup the full path in the config file.

This software is tested under linux. It should work under Windows or Mac with the pre-requisites installed,
but may require minor tweaks (bug reports are welcome).


## 1. Installation

### Via pip

This project is on the Python Package Index (Pypi) at [nhlv](https://pypi.org/project/nhlv), and can be
installed using `pip`.

1. Run `pip install nhlv`
2. Run `nhlv --init` to create a configuration directory and populate the `config` file
   with defaults and the required MLB.tv username and password. See the next section for more details.

### Archlinux

Install `nhlv` via the AUR.

This software is tested under linux. It should work under Windows or Mac with the pre-requisites installed, but may require minor tweaks.




## 2. Configuration

After installing, run:

    nhlv --init

This will create the initial config file/directory and populate it with the prompted NHL.tv username and password.
The `config` file will be located at `$HOME/.config/nhlv/config`. Directories are created if necessary.

Other properties in the config file are documented in the file itself. If you want to stream live or archived
games then you must provide valid login credentials (if you don't have NHL.tv you can still see scores and
watch highlights).

Some properties you may want to set in the `config` file:

* `username`: NHL.tv account username
* `password`: NHL.tv account password
* `use_rogers`: set to true if your NHL streaming account goes through Rogers
* `favs`: a comma-separated list of team codes which:
    - 1) are highlighted in the game data, and 
    - 2) are used for the default filter in the `-o/--filter` option (to show only the favourite team(s))
* `scores`: a boolean specifying whether or not you want to see scores in the game information. Warning: spoilers!
* `resolution`: the stream quality (passed in to streamlink). Use '720p_alt' for full HD at 60 frames/sec.
    - options are: 'worst', '224p', '288p', '360p', '504p', '540p', '720p', '720p_alt', 'best'


## 3. QUICKSTART

Here's a quick overview of the most common usage options:

    nhlv               # show today's schedule/scores
    nhlv -t wpg        # play today's Jets game, either live (if in-progress), or from the start (if archived)
    nhlv --recaps      # play all of today's recaps
    nhlv --standings   # show current standings



Help is available by running:

    nhlv --help   # short help
    nhlv --usage  # view full documenation


## 4. Default Behaviour: Show Schedule/Scores

Running `nhlv` by itself shows you the status of today's games, including scores (unless you've configured to hide scores by default).

### Scores/No-Scores

The `scores` option in the config file controls whether or not scores are shown. If false then no scores are
shown. Scores are also not shown before a feed is launched.

You can temporarily override the config file using either `-s/--scores` or `-n/--no-scores` options.



#### Usage note: shortening option arguments:

In general, you can shorten the long option names down to something unique. 

For example, rather than having to type `--yesterday` you can shorten it right down to `--y`.
However, you can one shorten `--tomorrow` down to `--to` since there is also the `--team` option which matches
up to `--t`.


### Dates and Filters

See the sections below on Dates and Filters for more information on specifying dates and filtering output based on
league, division, favourites, or arbitrary teams.


> Note on Arguments
> 
> Frequently used arguments have both a long form with double-dash `--` argument and a short form which uses a single dash `-`. 
> 
> For the long form arguments, you can shorten any option name down to the shortest unique value.  For example,
> rather than having to type `--yesterday` you can shorten it right down to `--y`.  However, you can only
> shorten `--tomorrow` down to `--to` since there is also the `--team` option (which makes `--t` non-unique).


## 5. Watching a Live or Archived Game

Watching a game is triggered by the `-t/--team TEAM` option. With this option the game stream (live or
archived) is launched for the given team. 

When passing `-t/--team TEAM` option, the stream is launched for the given team. By default the local feed
for the given team is chosen - i.e., it will follow the home/away feed appropriate for the team so that you
get the local team feed.  You can override the feed using the `-f/--feed` option. This works for either live
games or for archived games (e.g. if you use the `--date` option to select an earlier date).

Example:

    nhlv --team wpg          # play the live jets game
    nhlv --yesterday -t wpg  # play yesterday's jets game (see below for options on specifying dates)


### Feed Selection

By default the local feed for the given team is chosen - i.e., it will follow the home/away feed appropriate
for the given team so that you get the team's local feed if available.  You can override the feed using the
`-f/--feed` option. This works for either live games or for archived games (e.g. if you use the `--date`
option to select an earlier date).

    nhlv --team wpg --feed away  # choose the away feed (assuming Winnipeg is the home team, you will get the
                                 # opposing team's feed)


### Specifying Stream Start Location

For an in-progress game, the stream will join the live game at the current time. Use either  `--from-start` or
the `--inning` option to override this behaviour.

For an archived game, the stream will start from the beginning.

#### Start from Offset

For both live and archived games you can start from an offset time provided via the `--offset` option.
The offset is provide in form `HH:MM:SS`. Example:

    nhlv -t wpg --offset 01:00:00  # start today's Jets game an hour into the game


## 6. Record/Fetch


If you pass the `-f/--fetch` option, instead of launching the video player, the selected stream is saved to
disk. The stream is named to convention: `<date>-<away_team>-<home_team>-<feed>.ts`.

- Live games have extension `.ts`, highlight games are `.mp4`

Example: `2017-12-27-edm-wpg-national.ts`.

If your player supports it, you can select the stream to fetch, then manually launch your video player at a
later time while the stream is being saved to file. 

Example:

    nhlv --team wpg --fetch  # fetch the live jets game to disk. Most players let you view while downloading
                             # Most video players allow you to view while downloading


## 7. Highlights: Recap or Condensed Games

Playing the game highlight is triggered by using the `-f/--feed` option. The `recap` or `condensed` feeds show
up after a game has ended. To watch the highlight, specify one of those feeds along with the team name in the
`-t/--team` option.

Example:

    nhlv --team wpg -f condensed
    nhlv --team wpg -f recap

NOTE: You don't need login credentials to play highlights.


### Playing Multiple Game Recaps (for a given day)

The `--recaps` option lets you select a batch of game recaps to watch for a given day.
This option shows game recaps either for all games or for a selected set of teams (using a filter).
If no argument is given to `recaps` then no filter is applied.

Usage:

    --recaps ?filter?  : filter is optional, if not supplied then all games are selected

Examples:

    nhlv --recaps                       # show all available game recaps for today's games
    nhlv --yesterday --recaps           # show all available game recaps for yesterday's games
    nhlv --yesterday --recaps central   # show available game recaps for yesterday's games
                                        # in the Central division
    nhlv --yesterday --recaps wpg,ott   # show game recaps for yesterday's Winnipeg, Ottawa games
    nhlv --yesterday --recaps wpg,ott --fetch   # same as above but save to disk instead of view


## 8. Specifying Dates

You can specify the date to view using one of the following:

    -d|--date yyyy-mm-dd    # specific date
    --yesterday (or --yes)  # shortcut to yesterday
    --tomorrow  (or --tom)  # shortcut to tomorrow

For listing game data only (doesn't make sense for viewing), you can specify a number of days using the
`--days DAYS` option. Use this to show a schedule. It's useful with the `--filter` option to filter based on
favourite team(s).


## 9. Filters

You can filter the schedule/scores displays using the `-o/--filter` argument. 
The filter argument allows you to provide either a built-in filter name or a comma-separated list of team codes.

The filter option has the form:

    -o/--filter ?filter?  : where ?filter? is optional, and is either 
                            a 'filter name' or a comma-separated list of teams

> Note: -o is used as the short form because -f is taken. mnemonic: -o -> 'only'

> Note: Aside from the `--filter` command, other command arguments accept the same 'filter' string.
>       For example `--linescore ?filter?` and `--recaps ?filter?`


### Built-in Filters

If `?filter?` is not given then the built-in filter `favs` is used. `favs` is a filter which you can define 
in the config file to list your favourite team(s).

Other built-in filters are available which group teams by league and division. The filter names are:

* `east`, `atlantic`, `metropolitan` (Eastern Conference, Atlantic division, Metropolitan division)
* `west`, `central`, `pacific`       (Western Conference, Central division, Pacific division)

Using one of the above filter names will include those selected teams in the output.


### Ad-hoc Filters

You can also use any comma-separated list of team codes for a filter.

Examples:

    --filter wpg            # single team filter
    --filter wpg,ott,van    # multiple team filter
    -o wpg,ott,van          # same as above using shorter `-o` form

Note: Do not use spaces between commas unless you encapsulate the list in quotes.


## 10. Standings

You can display standings via the `--standings [category]` option. This option displays the given standings category then exits.

You can also specify a league or division filter via `-o/--filter`.

Standings categories:

* all
* division [default]
* conference
* wildcard
* league
* postseason
* preseason

By default, the division standings are displayed for today's date. 
You can add the `-d/--date yyyy-mm-dd` option to show standings for any given date.

You don't have to specify the full standings category, it will match any substring given. e.g. `--standings d`
will match division or `--standings wild` will match wildcard.

You can also use the `-o/--filter` option to narrow down what is displayed. e.g. `--standings division --filter ale`


## 11. Examples

Note: the common options have both short and long options. Both are shown in these examples.


### Live Games

    nhlv --team wpg               # play the live jets game. The feed is chosen based on jets being home vs. away
    nhlv -t wpg --feed national   # play live game, choose the national feed
    nhlv -t wpg --feed away       # play live game, choose the away feed. If jets are the home team this would choose
                                  # the opponent's feed

#### Archived Games

    nhlv --yesterday -t wpg         # play yesterday's jets game
    nhlv --date 2017-12-27 -t wpg   # watch the jets beat the oilers #spoiler

#### Highlights

Use the `--feed` option to select the highlight feed (`recap` or `condensed`):

    nhlv --yesterday -t wpg --feed condensed  # condensed feed
    nhlv --yesterday -t wpg -f recap          # recap feed

You can also use the `--recaps` option to show highlights for games on given day.
This will show all chosen recaps, one-by-one until finished. A highlight reel.


### Fetch

In these examples the game is saved to a file (.ts or .mp4) in the current directory.

    nhlv --team wpg --fetch
    nhlv --yesterday -t wpg -f recap --fetch   # fetch yesterday's recap

### Using `--days` for Schedule View

    nhlv --days 7           # show schedule for upcoming week
    nhlv --days 7 --filter  # show schedule for upcoming week, filtered on favourite teams (from config file)
    nhlv --days 7 --filter --favs 'wpg,ott' # show schedule filtered on favourite teams (from option)

#### Standings

    nhlv --standings                 # display division standings
    nhlv --standings div -o central  # display central division standings
    nhlv --standings conference      # display conference standings
    nhlv --standings conf -o west    # display western conference standings
    nhlv --standings league          # display overall league standings
    nhlv --standings all             # display all regular season standings categories

    nhlv --standings --date 2015-01-01  # display division standings for Jan 1, 2015
