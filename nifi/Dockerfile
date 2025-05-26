FROM apache/nifi:2.4.0

RUN curl -fSL "https://repo1.maven.org/maven2/org/apache/nifi/nifi-hadoop-nar/2.4.0/nifi-hadoop-nar-2.4.0.nar" --output /opt/nifi/nifi-current/lib/nifi-hadoop-nar-2.4.0.nar
RUN curl -fSL "https://repo1.maven.org/maven2/org/apache/nifi/nifi-hadoop-libraries-nar/2.4.0/nifi-hadoop-libraries-nar-2.4.0.nar" --output /opt/nifi/nifi-current/lib/nifi-hadoop-libraries-nar-2.4.0.nar
RUN curl -fSL "https://repo1.maven.org/maven2/org/apache/nifi/nifi-parquet-nar/2.4.0/nifi-parquet-nar-2.4.0.nar" --output /opt/nifi/nifi-current/lib/nifi-parquet-nar-2.4.0.nar
