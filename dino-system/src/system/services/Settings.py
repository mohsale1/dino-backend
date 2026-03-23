"""
System Settings Service
Manages system-wide settings including home page configuration
"""

from typing import Dict, Any
from src.repositories.HomePageInfoRepository import HomePageInfoRepository
from datetime import datetime


class SettingsService:
    """Service for managing system settings"""
    
    def __init__(self):
        self.homepage_repo = HomePageInfoRepository()
    
    def get_homepage_info(self) -> Dict[str, Any]:
        """Get home page information"""
        return self.homepage_repo.get_or_create_homepage_info()
    
    def update_homepage_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update home page information"""
        # Flatten nested structure for storage
        update_data = {}
        
        # Company info
        if 'company' in data:
            company = data['company']
            if company.get('name') is not None:
                update_data['company_name'] = company['name']
            if company.get('tagline') is not None:
                update_data['company_tagline'] = company['tagline']
            if company.get('description') is not None:
                update_data['company_description'] = company['description']
            if company.get('founded') is not None:
                update_data['company_founded'] = company['founded']
            if company.get('mission') is not None:
                update_data['company_mission'] = company['mission']
            if company.get('vision') is not None:
                update_data['company_vision'] = company['vision']
            if company.get('logo') is not None:
                update_data['company_logo'] = company['logo']
        
        # Contact info
        if 'contact' in data:
            contact = data['contact']
            if contact.get('email') is not None:
                update_data['contact_email'] = contact['email']
            if contact.get('phone') is not None:
                update_data['contact_phone'] = contact['phone']
            if contact.get('address') is not None:
                update_data['contact_address'] = contact['address']
            if contact.get('city') is not None:
                update_data['contact_city'] = contact['city']
            if contact.get('state') is not None:
                update_data['contact_state'] = contact['state']
            if contact.get('country') is not None:
                update_data['contact_country'] = contact['country']
            if contact.get('postal_code') is not None:
                update_data['contact_postal_code'] = contact['postal_code']
        
        # Social media
        if 'social_media' in data:
            social = data['social_media']
            if social.get('facebook') is not None:
                update_data['social_facebook'] = social['facebook']
            if social.get('twitter') is not None:
                update_data['social_twitter'] = social['twitter']
            if social.get('instagram') is not None:
                update_data['social_instagram'] = social['instagram']
            if social.get('linkedin') is not None:
                update_data['social_linkedin'] = social['linkedin']
            if social.get('youtube') is not None:
                update_data['social_youtube'] = social['youtube']
        
        # Hero section
        if 'hero' in data:
            hero = data['hero']
            if hero.get('title') is not None:
                update_data['hero_title'] = hero['title']
            if hero.get('subtitle') is not None:
                update_data['hero_subtitle'] = hero['subtitle']
            if hero.get('cta_text') is not None:
                update_data['hero_cta_text'] = hero['cta_text']
            if hero.get('cta_link') is not None:
                update_data['hero_cta_link'] = hero['cta_link']
            if hero.get('image') is not None:
                update_data['hero_image'] = hero['image']
            if hero.get('background_image') is not None:
                update_data['hero_background_image'] = hero['background_image']
        
        # Features section
        if 'features' in data:
            features = data['features']
            if features.get('enabled') is not None:
                update_data['features_enabled'] = features['enabled']
            if features.get('title') is not None:
                update_data['features_title'] = features['title']
            if features.get('subtitle') is not None:
                update_data['features_subtitle'] = features['subtitle']
        
        # Testimonials section
        if 'testimonials' in data:
            testimonials = data['testimonials']
            if testimonials.get('enabled') is not None:
                update_data['testimonials_enabled'] = testimonials['enabled']
            if testimonials.get('title') is not None:
                update_data['testimonials_title'] = testimonials['title']
            if testimonials.get('subtitle') is not None:
                update_data['testimonials_subtitle'] = testimonials['subtitle']
        
        # Stats section
        if 'stats' in data:
            stats = data['stats']
            if stats.get('enabled') is not None:
                update_data['stats_enabled'] = stats['enabled']
            if stats.get('title') is not None:
                update_data['stats_title'] = stats['title']
        
        # FAQ section
        if 'faq' in data:
            faq = data['faq']
            if faq.get('enabled') is not None:
                update_data['faq_enabled'] = faq['enabled']
            if faq.get('title') is not None:
                update_data['faq_title'] = faq['title']
            if faq.get('subtitle') is not None:
                update_data['faq_subtitle'] = faq['subtitle']
        
        # CTA section
        if 'cta' in data:
            cta = data['cta']
            if cta.get('enabled') is not None:
                update_data['cta_enabled'] = cta['enabled']
            if cta.get('title') is not None:
                update_data['cta_title'] = cta['title']
            if cta.get('subtitle') is not None:
                update_data['cta_subtitle'] = cta['subtitle']
            if cta.get('button_text') is not None:
                update_data['cta_button_text'] = cta['button_text']
            if cta.get('button_link') is not None:
                update_data['cta_button_link'] = cta['button_link']
        
        # SEO
        if 'seo' in data:
            seo = data['seo']
            if seo.get('title') is not None:
                update_data['seo_title'] = seo['title']
            if seo.get('description') is not None:
                update_data['seo_description'] = seo['description']
            if seo.get('keywords') is not None:
                update_data['seo_keywords'] = seo['keywords']
            if seo.get('image') is not None:
                update_data['seo_image'] = seo['image']
        
        # Theme
        if 'theme' in data:
            theme = data['theme']
            if theme.get('primary_color') is not None:
                update_data['theme_primary_color'] = theme['primary_color']
            if theme.get('secondary_color') is not None:
                update_data['theme_secondary_color'] = theme['secondary_color']
            if theme.get('accent_color') is not None:
                update_data['theme_accent_color'] = theme['accent_color']
        
        # Settings
        if 'settings' in data:
            settings = data['settings']
            if settings.get('show_login_button') is not None:
                update_data['show_login_button'] = settings['show_login_button']
            if settings.get('show_signup_button') is not None:
                update_data['show_signup_button'] = settings['show_signup_button']
            if settings.get('show_demo_button') is not None:
                update_data['show_demo_button'] = settings['show_demo_button']
            if settings.get('maintenance_mode') is not None:
                update_data['maintenance_mode'] = settings['maintenance_mode']
            if settings.get('maintenance_message') is not None:
                update_data['maintenance_message'] = settings['maintenance_message']
        
        # Add timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update in database
        return self.homepage_repo.update_homepage_info(update_data)