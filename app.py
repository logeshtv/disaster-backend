"""
Main Flask application for disaster relief system
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import datetime
import sys
from models import init_db, get_db, Hub, Donation, VictimRequest, DisasterEvent
from utils.disaster_utils import (
    extract_location_from_tweet,
    geocode_location,
    find_nearby_hubs,
    find_best_hub_for_request,
    classify_disaster_type,
    assess_severity
)

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize database
init_db()

ADMIN_KEY = os.getenv('ADMIN_KEY', 'admin123')

# Server start time
SERVER_START_TIME = datetime.now()


@app.route('/health', methods=['GET'])
def health_check():
    """
    Enhanced health check endpoint with server information
    """
    try:
        # Test database connection
        db = get_db()
        hubs_count = db.query(Hub).count()
        donations_count = db.query(Donation).count()
        requests_count = db.query(VictimRequest).count()
        events_count = db.query(DisasterEvent).count()
        db.close()
        
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
        hubs_count = donations_count = requests_count = events_count = 0
    
    uptime = datetime.now() - SERVER_START_TIME
    uptime_seconds = int(uptime.total_seconds())
    uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
    
    return jsonify({
        'status': 'healthy',
        'message': '✅ Disaster Relief API Server is Running',
        'server': {
            'name': 'Disaster Relief Management System',
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'development'),
            'python_version': sys.version.split()[0],
            'host': '0.0.0.0',
            'port': 5000,
            'ipv4_enabled': True,
            'ipv6_enabled': True
        },
        'uptime': {
            'started_at': SERVER_START_TIME.isoformat(),
            'uptime': uptime_str,
            'uptime_seconds': uptime_seconds
        },
        'database': {
            'status': db_status,
            'statistics': {
                'hubs': hubs_count,
                'donations': donations_count,
                'victim_requests': requests_count,
                'disaster_events': events_count
            }
        },
        'endpoints': {
            'health': '/health',
            'predict_location': '/api/predict-location',
            'admin_auth': '/api/admin/auth',
            'hubs': '/api/admin/hubs',
            'donations': '/api/donations',
            'victim_requests': '/api/victim-requests',
            'dashboard': '/api/dashboard/stats'
        },
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/predict-location', methods=['POST'])
def predict_location():
    """
    Predict location from disaster tweet
    Input: {"tweet": "Earthquake hits Tokyo"}
    Output: {"location": "Tokyo", "latitude": 35.6762, "longitude": 139.6503, ...}
    """
    try:
        data = request.get_json()
        tweet = data.get('tweet', '')
        
        if not tweet:
            return jsonify({'error': 'Tweet text is required'}), 400
        
        # Extract location using NER model
        location = extract_location_from_tweet(tweet)
        
        if not location:
            return jsonify({
                'success': False,
                'message': 'No location detected in tweet',
                'tweet': tweet
            }), 200
        
        # Geocode location
        coords = geocode_location(location)
        
        if not coords:
            return jsonify({
                'success': False,
                'message': f'Could not geocode location: {location}',
                'detected_location': location,
                'tweet': tweet
            }), 200
        
        latitude, longitude = coords
        
        # Get nearby hubs
        db = get_db()
        all_hubs = db.query(Hub).all()
        hubs_list = [hub.to_dict() for hub in all_hubs]
        nearby_hubs = find_nearby_hubs((latitude, longitude), hubs_list, max_distance_km=100)
        
        # Classify disaster type and severity
        disaster_type = classify_disaster_type(tweet)
        severity = assess_severity(tweet)
        
        # Save disaster event
        disaster_event = DisasterEvent(
            tweet_text=tweet,
            detected_location=location,
            latitude=latitude,
            longitude=longitude,
            disaster_type=disaster_type,
            severity=severity,
            nearby_hubs_count=len(nearby_hubs)
        )
        db.add(disaster_event)
        db.commit()
        db.refresh(disaster_event)
        
        # Get the event_id before closing the session
        event_id = disaster_event.id
        
        db.close()
        
        return jsonify({
            'success': True,
            'detected_location': location,
            'latitude': latitude,
            'longitude': longitude,
            'disaster_type': disaster_type,
            'severity': severity,
            'nearby_hubs': nearby_hubs,
            'tweet': tweet,
            'event_id': event_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/auth', methods=['POST'])
def admin_auth():
    """
    Admin authentication
    Input: {"key": "admin123"}
    """
    try:
        data = request.get_json()
        key = data.get('key', '')
        
        if key == ADMIN_KEY:
            return jsonify({'success': True, 'message': 'Authentication successful'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid admin key'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/hubs', methods=['GET', 'POST'])
def manage_hubs():
    """
    GET: Get all hubs
    POST: Create new hub (admin only)
    """
    db = get_db()
    
    try:
        if request.method == 'GET':
            hubs = db.query(Hub).all()
            return jsonify({
                'success': True,
                'hubs': [hub.to_dict() for hub in hubs]
            }), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Verify admin key
            admin_key = request.headers.get('X-Admin-Key')
            if admin_key != ADMIN_KEY:
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Geocode if coordinates not provided
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not latitude or not longitude:
                coords = geocode_location(data.get('location_name'))
                if coords:
                    latitude, longitude = coords
                else:
                    return jsonify({'error': 'Could not geocode location'}), 400
            
            hub = Hub(
                name=data.get('name'),
                location_name=data.get('location_name'),
                latitude=float(latitude),
                longitude=float(longitude),
                inventory=data.get('inventory', {}),
                contact=data.get('contact', '')
            )
            
            db.add(hub)
            db.commit()
            db.refresh(hub)
            
            return jsonify({
                'success': True,
                'message': 'Hub created successfully',
                'hub': hub.to_dict()
            }), 201
            
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/hubs/<int:hub_id>', methods=['PUT', 'DELETE'])
def update_delete_hub(hub_id):
    """
    PUT: Update hub
    DELETE: Delete hub
    """
    db = get_db()
    
    try:
        # Verify admin key
        admin_key = request.headers.get('X-Admin-Key')
        if admin_key != ADMIN_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        
        hub = db.query(Hub).filter(Hub.id == hub_id).first()
        if not hub:
            return jsonify({'error': 'Hub not found'}), 404
        
        if request.method == 'PUT':
            data = request.get_json()
            
            if 'name' in data:
                hub.name = data['name']
            if 'location_name' in data:
                hub.location_name = data['location_name']
            if 'latitude' in data:
                hub.latitude = float(data['latitude'])
            if 'longitude' in data:
                hub.longitude = float(data['longitude'])
            if 'inventory' in data:
                hub.inventory = data['inventory']
            if 'contact' in data:
                hub.contact = data['contact']
            
            db.commit()
            db.refresh(hub)
            
            return jsonify({
                'success': True,
                'message': 'Hub updated successfully',
                'hub': hub.to_dict()
            }), 200
        
        elif request.method == 'DELETE':
            db.delete(hub)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Hub deleted successfully'
            }), 200
            
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/donations', methods=['GET', 'POST'])
def manage_donations():
    """
    GET: Get all donations
    POST: Create new donation
    """
    db = get_db()
    
    try:
        if request.method == 'GET':
            donations = db.query(Donation).all()
            return jsonify({
                'success': True,
                'donations': [donation.to_dict() for donation in donations]
            }), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            donation = Donation(
                donor_name=data.get('donor_name'),
                donor_email=data.get('donor_email', ''),
                donor_phone=data.get('donor_phone', ''),
                items=data.get('items', {}),
                amount=float(data.get('amount', 0)),
                notes=data.get('notes', ''),
                payment_info=data.get('payment_info', {}),
                tracking_status=data.get('tracking_status', 'pending'),
                tracking_history=data.get('tracking_history', [])
            )
            
            db.add(donation)
            db.commit()
            db.refresh(donation)
            
            return jsonify({
                'success': True,
                'message': 'Donation recorded successfully',
                'donation': donation.to_dict()
            }), 201
            
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/donations', methods=['GET'])
def admin_list_donations():
    """
    Admin: list all donations (requires X-Admin-Key header)
    """
    admin_key = request.headers.get('X-Admin-Key')
    if admin_key != ADMIN_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    try:
        donations = db.query(Donation).order_by(Donation.created_at.desc()).all()
        return jsonify({'success': True, 'donations': [d.to_dict() for d in donations]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/admin/donations/<int:donation_id>', methods=['PUT'])
def admin_update_donation(donation_id):
    """
    Admin: update donation status/tracking information
    Payload may include: allocated_status, tracking_status, tracking_note, hub_id
    """
    admin_key = request.headers.get('X-Admin-Key')
    if admin_key != ADMIN_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    db = get_db()
    try:
        donation = db.query(Donation).filter(Donation.id == donation_id).first()
        if not donation:
            return jsonify({'error': 'Donation not found'}), 404

        # Update simple fields
        if 'allocated_status' in data:
            donation.allocated_status = data.get('allocated_status')
        if 'tracking_status' in data:
            donation.tracking_status = data.get('tracking_status')

        # Append tracking history entry if provided
        tracking_note = data.get('tracking_note')
        if tracking_note:
            entry = {
                'status': donation.tracking_status,
                'note': tracking_note,
                'timestamp': datetime.utcnow().isoformat()
            }
            # include hub id when given
            if 'hub_id' in data:
                entry['hub_id'] = data.get('hub_id')

            history = donation.tracking_history or []
            history.append(entry)
            donation.tracking_history = history

        db.commit()
        db.refresh(donation)

        return jsonify({'success': True, 'donation': donation.to_dict()}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/victim-requests', methods=['GET', 'POST'])
def manage_victim_requests():
    """
    GET: Get all victim requests
    POST: Create new victim request
    """
    db = get_db()
    
    try:
        if request.method == 'GET':
            requests_query = db.query(VictimRequest).all()
            return jsonify({
                'success': True,
                'requests': [req.to_dict() for req in requests_query]
            }), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Geocode location
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not latitude or not longitude:
                coords = geocode_location(data.get('location_name'))
                if coords:
                    latitude, longitude = coords
            
            victim_request = VictimRequest(
                victim_name=data.get('victim_name'),
                victim_phone=data.get('victim_phone', ''),
                location_name=data.get('location_name'),
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                requested_items=data.get('requested_items', {}),
                urgency=data.get('urgency', 'medium'),
                notes=data.get('notes', '')
            )
            
            db.add(victim_request)
            db.commit()
            db.refresh(victim_request)
            
            # Try to match with best hub
            if latitude and longitude:
                all_hubs = db.query(Hub).all()
                hubs_list = [hub.to_dict() for hub in all_hubs]
                best_hub = find_best_hub_for_request(
                    (latitude, longitude),
                    data.get('requested_items', {}),
                    hubs_list
                )
                
                result = {
                    'success': True,
                    'message': 'Request created successfully',
                    'request': victim_request.to_dict(),
                    'matched_hub': best_hub
                }
            else:
                result = {
                    'success': True,
                    'message': 'Request created successfully',
                    'request': victim_request.to_dict(),
                    'matched_hub': None
                }
            
            return jsonify(result), 201
            
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    db = get_db()
    
    try:
        total_hubs = db.query(Hub).count()
        total_donations = db.query(Donation).count()
        total_requests = db.query(VictimRequest).count()
        total_events = db.query(DisasterEvent).count()
        
        pending_requests = db.query(VictimRequest).filter(
            VictimRequest.fulfilled_status == 'pending'
        ).count()
        
        recent_events = db.query(DisasterEvent).order_by(
            DisasterEvent.created_at.desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_hubs': total_hubs,
                'total_donations': total_donations,
                'total_requests': total_requests,
                'total_events': total_events,
                'pending_requests': pending_requests
            },
            'recent_events': [event.to_dict() for event in recent_events]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
