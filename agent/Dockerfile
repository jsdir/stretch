# agent

FROM ubuntu:12.10
MAINTAINER Jason Sommer "gatoralli69@gmail.com"

ADD agent /usr/local/share/stretch-agent

#RUN apt-get install -y nginx php5 php5-cgi php5-fpm

# nginx config
#RUN sed -i -e"s/keepalive_timeout\s*65/keepalive_timeout 2/" /etc/nginx/nginx.conf
#RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# php-fpm config
#RUN sed -i -e "s/;cgi.fix_pathinfo=1/cgi.fix_pathinfo=0/g" /etc/php5/fpm/php.ini
#RUN sed -i -e "s/;daemonize\s*=\s*yes/daemonize = no/g" /etc/php5/fpm/php-fpm.conf

# Load files
#ADD files /usr/share/stretch/files
#ADD app /usr/share/stretch/app

# Nginx site conf
#RUN rm /etc/nginx/sites-available/default
#RUN ln -s /usr/share/stretch/files/nginx.conf /etc/nginx/sites-available/default

# Start supervisor
#RUN ln -s /usr/share/stretch/files/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

#CMD ["/usr/bin/supervisord", "-n"]
