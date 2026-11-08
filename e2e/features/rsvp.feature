Feature: Responding to a pub
  Members say whether they are coming from the event page. The page updates in place, without reloading.

  Scenario: Saying yes, then changing my mind
    Given I am signed in as a member
    And the next pub is at "The Anchor"
    When I open the next pub's page
    And I note that the page has not reloaded yet
    Then I should see "You have not responded to this pub yet."
    And I should see "Attendees (0)"
    When I click the "I'm coming!" button
    Then I should see "You said yes to this pub via this web interface."
    And I should see "Attendees (1)"
    When I click the "I'm not coming anymore!" button
    Then I should see "You said no to this pub via this web interface."
    And I should see "Attendees (0)"
    When I click the "I'm actually coming" button
    Then I should see "You said yes to this pub via this web interface."
    And I should see "Attendees (1)"
    And the page should not have reloaded
    And there should be no JavaScript errors

  Scenario: Coming after skipping a pub
    Given I am signed in as a member using AutoPub
    And the next pub is at "The Anchor"
    And I am going to it through AutoPub
    And I have skipped the next pub
    When I open the next pub's page
    Then I should see "You have opted-in to AutoPub but skipped the next pub."
    And I should see "Attendees (0)"
    When I click the "I'm coming!" button
    Then I should see "You said yes to this pub via this web interface."
    And I should see "Attendees (1)"
