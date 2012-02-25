pricegrab
---------

evolution of an api

- a simple price service, one call
    

- we now add a new method on for trains
    - client unchanged

- we now run multiple copies of the server behind a wsgi load balancer
    - client unchanged

- some data can be cached 
    - client unchanged

- we now shard some requests elsewhere (trains)
    - client unchanged

