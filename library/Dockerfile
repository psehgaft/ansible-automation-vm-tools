FROM ghcr.io/nautobot/nautobot:1.5.21-py3.10


# RUN rm -rf /opt/nautobot/jobs 
RUN mkdir -p /opt/nautobot/jobs

#RUN chgrp -R 0 /opt/nautobot/jobs 
RUN chmod -R g=u /opt/nautobot/jobs


USER 1001
