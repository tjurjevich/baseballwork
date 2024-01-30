This project was completed for my master's level deterministic operations research course.

Project objective: Create a Gurobi model to determine the optimal house to hypothetically purchase so as to minimize the number of expected miles driven throughout the week. Various constraints are provided concerning a home's features (listing price, # bedrooms, # bathrooms, and square footage). The objective function aims to provide a rough estimate of driven miles, and is comprised of the following destinations:

  > Place of work
  > Gym
  > Provided WalMart
  > Provided Sam's Club
  > 3 Jimmy John's locations (only 1 of which is used in the model's calculation)
  > 2 Runza locations (only 1 of which is used in the model's calculation)
  > Parent's House

Multiplying constants for each destination are based on the number of round trips I have listed per week per destination.
