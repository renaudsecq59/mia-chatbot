FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html article.html veille.html confidentialite.html etudes-de-cas.html mia-agency.html callback.html preview.html /usr/share/nginx/html/
COPY photo-000.jpg /usr/share/nginx/html/

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
