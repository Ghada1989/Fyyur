# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
from typing import List, Any

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import config
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy import and_

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

venue_genres = db.Table('venue_genres',
                        db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True),
                        db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True)
                        )

artist_genres = db.Table('artist_genres',
                         db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
                         db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True)
                         )


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=venue_genres,
                             backref=db.backref('venues', lazy=True))
    shows = db.relationship('Show', backref='venue', lazy=True)


class Genre(db.Model):
    __tablename__ = 'Genre'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=artist_genres,
                             backref=db.backref('artists', lazy=True))
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    show_date = db.Column(db.DateTime, nullable=False)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
def prepare_data_for_display(venues_based_cities, num_venue_show):
    data = []
    for key, value in venues_based_cities.items():
        venues = []
        for venue in value:
            venues.append({
                        "id": venue.id,
                        "name": venue.name,
                        "num_upcoming_shows": num_venue_show.get(venue.id),
                    })

        data.append(
            {
                "city": venue.city,
                "state": venue.state,
                "venues": venues
            }
        )
    return data


@app.route('/venues')
def venues():
    try:
        data = []
        num_venue_show = {}
        venues = db.session.query(Venue.id, Venue.city, Venue.state, Venue.name).all()
        venue_shows = db.session.query(Venue.id, func.count(Show.id)).join(Show, Show.show_date >= datetime.today(), isouter=True).group_by(Show.id, Venue.id).all()
        for shows in venue_shows:
            num_venue_show.update({shows[0]: shows[1]})

        venues_based_cities = {}
        for venue in venues:
            if venue.city not in venues_based_cities.keys():
                venues_based_cities.update({
                    venue.city: [venue]
                })
            else:
                venues_based_cities.get(venue.city).append(venue)

        data = prepare_data_for_display(venues_based_cities, num_venue_show)
    except Exception as excep:
        print(excep)
    finally:
        db.session.close()
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_string = request.form.get('search_term')
    result = list(Venue.query.filter(Venue.name.ilike('%' + str(search_string) +'%')))
    response = {
        "count": len(result),
        "data": result
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = {}
    try:
        venue = Venue.query.get(venue_id)
        upcoming_shows = list(Show.query.filter(and_(Show.venue_id == venue_id, Show.show_date >= datetime.today())))
        past_shows = list(Show.query.filter(and_(Show.venue_id == venue_id, Show.show_date < datetime.today())))

        data = {
            "id": venue.id,
            "name": venue.name,
            "genres": venue.genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": venue.phone,
            "website": venue.facebook_link,
            "facebook_link": venue.facebook_link,
            "seeking_talent": True,
            "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows),
        }

    except Exception as excep:
        print(excep)
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        venue = Venue(
            name=request.form['name'],
            city=request.form['city'],
            state=request.form['state'],
            address=request.form['address'],
            phone=request.form['phone'],
            image_link=request.form['image_link'],
            facebook_link=request.form['facebook_link'],
        )
        genres: Genre = []
        for genre in request.form.getlist('genres'):
            genres.append(Genre.query.filter_by(name=genre).first())

        venue.genres = genres

        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully listed!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.')

    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
    try:
        Show.query.filter_by(venue_id= venue_id).delete()
        venue = Venue.query.get(venue_id)
        venue.genres = []
        db.session.add(venue)
        db.session.delete(venue)
        db.session.commit()

        flash('The venue was successfully deleted!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. The venue could not be delete.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    return render_template('pages/artists.html', artists=list(Artist.query.all()))


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_string = request.form.get('search_term')
    result = list(Artist.query.filter(Artist.name.ilike('%' + str(search_string) +'%')))
    response = {
        "count": len(result),
        "data": result
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = {}
    try:
        artist = Artist.query.get(artist_id)
        upcoming_shows = list(Show.query.filter(and_(Show.artist_id == artist_id, Show.show_date >= datetime.today())))
        past_shows = list(Show.query.filter(and_(Show.artist_id == artist_id, Show.show_date < datetime.today())))
        data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.facebook_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": True,
        "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }
    except Exception as excep:
        print(excep)

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist=Artist.query.get(artist_id)
    genres = artist.genres
    display_genres = []
    for g in genres:
        display_genres.append(g.name)
    artist.display_genres = display_genres

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        artist=Artist.query.get(artist_id)
        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link']
        genres: Genre = []
        for genre in request.form.getlist('genres'):
            genres.append(Genre.query.filter_by(name=genre).first())

        artist.genres = genres
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + artist.name + ' was successfully updated!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. Artist ' + artist.name + ' could not be updated.')

    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue=Venue.query.get(venue_id)
    genres = venue.genres
    display_genres = []
    for g in genres:
        display_genres.append(g.name)
    venue.display_genres = display_genres

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        venue=Venue.query.get(venue_id)
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.phone = request.form['phone']
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']

        genres: Genre = []
        for genre in request.form.getlist('genres'):
            genres.append(Genre.query.filter_by(name=genre).first())
        venue.genres = genres
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully updated!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be updated.')

    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        artist = Artist(
            name=request.form['name'],
            city=request.form['city'],
            state=request.form['state'],
            phone=request.form['phone'],
            facebook_link=request.form['facebook_link'],
        )
        genres: Genre = []
        for genre in request.form.getlist('genres'):
            genres.append(Genre.query.filter_by(name=genre).first())

        artist.genres = genres

        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + artist.name + ' was successfully listed!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. Artist ' + artist.name + ' could not be listed.')

    finally:
        db.session.close()
    return render_template('pages/home.html')

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows = list(Show.query.all())
    data = []
    for show in shows:
        data.append({
        "venue_id": show.venue_id,
        "venue_name": show.venue.name,
        "artist_id": show.artist_id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": str(show.show_date)
        })

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    try:
        show = Show(
        venue_id=request.form['venue_id'],
        artist_id=request.form['artist_id'],
        show_date=request.form['start_time']
        )

        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')

    except Exception as excep:
        print(excep)
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')

    finally:
        db.session.close()
    return render_template('pages/home.html')




@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
