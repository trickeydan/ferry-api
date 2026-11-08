Feature: Finding my way around
  Members move between the home page and the Ferries and Pub areas.

  Scenario: The home page links to the Ferries area
    Given I am signed in as a member
    When I open "/"
    And I click the "Ferries" link
    Then I should be on "/ferries/"
    And the "Overview" tab should be active

  Scenario: The Pub area has a tab for each page
    Given I am signed in as a member
    When I open "/pub/"
    Then the "Overview" tab should be active
    When I click the "Pubs" link
    Then I should be on "/pub/pubs/"
    And the "Pubs" tab should be active

  Scenario: An event page links back to the events list
    Given I am signed in as a member
    And the next pub is at "The Anchor"
    When I open "/pub/events"
    And I click the "View" link
    Then I should see "The Anchor"
    When I click the "← Events" link
    Then I should be on "/pub/events"
