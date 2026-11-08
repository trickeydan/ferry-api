Feature: Pubs
  Anyone can add a pub. Only admins choose which pub is the default.

  Scenario: Adding a pub with the emoji picker
    Given I am signed in as a member
    When I open "/pub/pubs/new/"
    And I fill in "Name" with "The Crown"
    And I pick the "beer" emoji
    And I fill in "Map url" with "https://example.com/crown"
    And I click the "Add Pub" button
    Then I should be on "/pub/pubs/"
    And I should see "Added The Crown."
    And the pub "The Crown" should have an emoji

  Scenario: Members cannot make a pub the default
    Given I am signed in as a member
    And there is a pub called "The Anchor"
    When I open "/pub/pubs/"
    Then I should see "The Anchor"
    And I should not see a "Make default" button

  Scenario: An admin makes a pub the default
    Given I am signed in as an admin
    And there is a pub called "The Anchor"
    And there is a pub called "The Crown"
    And "The Anchor" is the default pub
    When I open "/pub/pubs/"
    And I make "The Crown" the default pub
    Then "The Crown" should be the default pub
    And "The Anchor" should not be the default pub
