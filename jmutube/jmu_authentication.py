from django.contrib.auth.models import User
from random import Random
import string
import ldap
import django.dispatch

user_authenticated = django.dispatch.Signal(providing_args=["username"])

class Jmu_Authentication_Backend:
    """
    Authenticate against the JMU LDAP server
    """
    def authenticate(self, username=None, password=None):
        
        base = 'ou=People,o=jmu'
                
        try:
            username = username.strip()
            cn = 'cn=%s' % username
            l = ldap.open("ldap.jmu.edu")
            l.protocol_version = ldap.VERSION2
            l.simple_bind_s(cn + ',' + base, password)
        
            try:
                user = User.objects.get(username=username)

            except User.DoesNotExist:

                result = l.search_s(base, ldap.SCOPE_ONELEVEL, cn,
                                    attrlist=['sn', 'mail', 'givenName', 'eduPersonPrimaryAffiliation'])
                                
                if (len(result) != 1):
                                        return None
                attributes = result[0][1]
                attributes['sn'] = attributes['sn'][:1] # only use first sn attribute
                for attribute in attributes:
                    attributes[attribute] = ' '.join(attributes[attribute])

                if (not attributes['eduPersonPrimaryAffiliation'] in
                    ['staff','faculty','administrator']):
                                        return None

                pwd = ''.join(Random().sample(string.letters + string.digits, 20))
                user = User(username=username, password=pwd)
                user.first_name = attributes['givenName'][:30]
                user.last_name = attributes['sn'][:30]
                user.email = attributes['mail']
                user.save()
                
            user_authenticated.send(sender=self, username=user.username)    
            return user
        
        except ldap.LDAPError, error_message:
            return None
    
        finally:
            if (l):
                l.unbind_s()
        
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
